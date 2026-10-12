from collections.abc import Callable
from datetime import date, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db import download_stats
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
)
from cms_backend.mill.context import Context as MillContext
from cms_backend.mill.fetch_lb_download_stats import fetch_download_stats
from cms_backend.utils.filename import DownloadLocation


@pytest.fixture(autouse=True)
def configured_context(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(Context, "download_stats_days_ago", 2)
    monkeypatch.setattr(Context, "download_stats_yesterday_hour", 4)
    monkeypatch.setattr(MillContext, "download_stats_request_delay", 0)


def _create_prod_book(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
) -> Title:
    title = create_title(name="wikipedia_en_all", flavours=["all"])
    collection = create_collection(
        name="lb",
        download_base_url="https://lb.download.kiwix.org/",
        title_ids_with_paths=[(title.id, "zim/")],
    )
    collection_title = dbsession.scalars(
        select(CollectionTitle).where(CollectionTitle.collection_id == collection.id)
    ).one()
    book = create_book(
        title_id=title.id,
        flavour="all",
        filename="foo_en_all_2026-01.zim",
        location_kind="prod",
    )
    create_book_location(
        book=book,
        warehouse_id=collection.warehouse_id,
        path=collection_title.path,
        filename="foo_en_all_2026-01.zim",
    )
    return title


def _mapped_path(dbsession: OrmSession) -> DownloadLocation:
    return next(iter(download_stats.get_prod_download_location_map(dbsession)))


def test_fetch_stores_downloads_and_marks_days(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    title = _create_prod_book(
        dbsession, create_title, create_collection, create_book, create_book_location
    )
    path = _mapped_path(dbsession)

    with (
        patch(
            "cms_backend.mill.fetch_lb_download_stats.getnow",
            return_value=datetime(2026, 10, 6, 5, 0),
        ),
        patch(
            "cms_backend.mill.fetch_lb_download_stats.fetch_download_stats_for_day",
            return_value={path: 3},
        ) as mock_fetch,
    ):
        fetch_download_stats(dbsession)

    assert mock_fetch.call_count == 2
    assert download_stats.get_fetched_days(
        dbsession, start=date(2026, 10, 1), end=date(2026, 10, 31)
    ) == {date(2026, 10, 4), date(2026, 10, 5)}
    for day in (date(2026, 10, 4), date(2026, 10, 5)):
        assert download_stats.get_downloads_for_flavour(
            dbsession, title_id=title.id, flavour="all", start=day, end=day
        ) == {day: 3}


def test_fetch_does_not_refetch_completed_days(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    _create_prod_book(
        dbsession, create_title, create_collection, create_book, create_book_location
    )
    path = _mapped_path(dbsession)
    download_stats.mark_day_fetched(dbsession, day=date(2026, 10, 4), nb_downloads=1)

    with (
        patch(
            "cms_backend.mill.fetch_lb_download_stats.getnow",
            return_value=datetime(2026, 10, 6, 5, 0),
        ),
        patch(
            "cms_backend.mill.fetch_lb_download_stats.fetch_download_stats_for_day",
            return_value={path: 3},
        ) as mock_fetch,
    ):
        fetch_download_stats(dbsession)

    assert mock_fetch.call_count == 1
    assert mock_fetch.call_args.args[0] == date(2026, 10, 5)


def test_fetch_respects_yesterday_gate(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    _create_prod_book(
        dbsession, create_title, create_collection, create_book, create_book_location
    )
    path = _mapped_path(dbsession)

    with (
        patch(
            "cms_backend.mill.fetch_lb_download_stats.getnow",
            return_value=datetime(2026, 10, 6, 3, 0),
        ),
        patch(
            "cms_backend.mill.fetch_lb_download_stats.fetch_download_stats_for_day",
            return_value={path: 3},
        ) as mock_fetch,
    ):
        fetch_download_stats(dbsession)

    # yesterday (2026-10-05) is not yet available before 4am, only 10-04 is
    assert mock_fetch.call_count == 1
    assert mock_fetch.call_args.args[0] == date(2026, 10, 4)


def test_fetch_failure_leaves_day_unmarked(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    _create_prod_book(
        dbsession, create_title, create_collection, create_book, create_book_location
    )

    with (
        patch(
            "cms_backend.mill.fetch_lb_download_stats.getnow",
            return_value=datetime(2026, 10, 6, 5, 0),
        ),
        patch(
            "cms_backend.mill.fetch_lb_download_stats.fetch_download_stats_for_day",
            side_effect=ValueError("boom"),
        ),
    ):
        fetch_download_stats(dbsession)

    assert (
        download_stats.get_fetched_days(
            dbsession, start=date(2026, 10, 1), end=date(2026, 10, 31)
        )
        == set()
    )


def test_fetch_purges_old_stats(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(Context, "download_stats_days_ago", 0)
    title = create_title(name="wikipedia_en_all", flavours=["all"])
    download_stats.replace_day_stats(
        dbsession,
        day=date(2024, 5, 1),
        counts={download_stats.TitleFlavourKey(title_id=title.id, flavour="all"): 1},
    )
    download_stats.mark_day_fetched(dbsession, day=date(2024, 5, 1), nb_downloads=1)

    with patch(
        "cms_backend.mill.fetch_lb_download_stats.getnow",
        return_value=datetime(2026, 10, 6, 5, 0),
    ):
        fetch_download_stats(dbsession)

    assert (
        download_stats.get_fetched_days(
            dbsession, start=date(2024, 1, 1), end=date(2024, 12, 31)
        )
        == set()
    )
