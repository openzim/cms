from collections.abc import Callable
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.download_stats import (
    TitleFlavourKey,
    get_downloads_for_flavour,
    get_fetched_days,
    get_prod_download_location_map,
    mark_day_fetched,
    purge_old_stats,
    replace_day_stats,
    unmark_day_fetched,
)
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
)
from cms_backend.utils.filename import (
    construct_download_url,
    normalize_download_location,
)


def _tf(title_id: UUID, flavour: str) -> TitleFlavourKey:
    return TitleFlavourKey(title_id=title_id, flavour=flavour)


def _create_prod_book(
    *,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    dbsession: OrmSession,
    download_base_url: str = "https://lb.download.kiwix.org/",
    path: str = "zim/",
    flavour: str = "all",
    filename: str = "foo_en_all_2026-01.zim",
) -> tuple[Title, Collection]:
    title = create_title(name="wikipedia_en_all", flavours=[flavour])
    collection = create_collection(
        name="lb",
        download_base_url=download_base_url,
        title_ids_with_paths=[(title.id, path)],
    )
    collection_title = dbsession.scalars(
        select(CollectionTitle).where(CollectionTitle.collection_id == collection.id)
    ).one()
    book = create_book(
        title_id=title.id,
        flavour=flavour,
        name=filename.removesuffix(".zim"),
        filename=filename,
        location_kind="prod",
    )
    create_book_location(
        book=book,
        warehouse_id=collection.warehouse_id,
        path=collection_title.path,
        filename=filename,
    )
    return title, collection


def test_get_prod_download_location_map(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    title, _ = _create_prod_book(
        create_title=create_title,
        create_collection=create_collection,
        create_book=create_book,
        create_book_location=create_book_location,
        dbsession=dbsession,
    )

    expected_location = normalize_download_location(
        construct_download_url(
            "https://lb.download.kiwix.org/",
            Path("zim/"),
            "foo_en_all_2026-01.zim",
        )
    )
    assert get_prod_download_location_map(dbsession) == {
        expected_location: TitleFlavourKey(title_id=title.id, flavour="all")
    }


def test_get_prod_download_location_map_ignores_non_prod(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    title, _ = _create_prod_book(
        create_title=create_title,
        create_collection=create_collection,
        create_book=create_book,
        create_book_location=create_book_location,
        dbsession=dbsession,
    )
    # Move the only book out of production
    book = dbsession.scalars(select(Book).where(Book.title_id == title.id)).one()
    book.location_kind = "staging"
    dbsession.flush()

    assert get_prod_download_location_map(dbsession) == {}


def test_replace_day_stats_clears_stale_values(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    title = create_title(name="wikipedia_en_all", flavours=["all", "maxi"])
    day = date(2026, 3, 1)

    total = replace_day_stats(
        dbsession,
        day=day,
        counts={_tf(title.id, "all"): 5, _tf(title.id, "maxi"): 2},
    )
    assert total == 7
    assert get_downloads_for_flavour(
        dbsession, title_id=title.id, flavour="all", start=day, end=day
    ) == {day: 5}

    # Refetching the day must drop the now absent "all" flavour
    replace_day_stats(dbsession, day=day, counts={_tf(title.id, "maxi"): 3})
    assert (
        get_downloads_for_flavour(
            dbsession, title_id=title.id, flavour="all", start=day, end=day
        )
        == {}
    )
    assert get_downloads_for_flavour(
        dbsession, title_id=title.id, flavour="maxi", start=day, end=day
    ) == {day: 3}


def test_replace_day_stats_ignores_non_positive(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    title = create_title(name="wikipedia_en_all", flavours=["all"])
    day = date(2026, 3, 1)

    assert replace_day_stats(dbsession, day=day, counts={_tf(title.id, "all"): 0}) == 0
    assert (
        get_downloads_for_flavour(
            dbsession, title_id=title.id, flavour="all", start=day, end=day
        )
        == {}
    )


def test_replace_day_stats_leap_year(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    title = create_title(name="wikipedia_en_all", flavours=["all"])

    replace_day_stats(
        dbsession, day=date(2024, 2, 29), counts={_tf(title.id, "all"): 4}
    )
    replace_day_stats(dbsession, day=date(2024, 3, 1), counts={_tf(title.id, "all"): 6})

    assert get_downloads_for_flavour(
        dbsession,
        title_id=title.id,
        flavour="all",
        start=date(2024, 2, 28),
        end=date(2024, 3, 2),
    ) == {date(2024, 2, 29): 4, date(2024, 3, 1): 6}


def test_get_downloads_for_flavour_spans_years(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    title = create_title(name="wikipedia_en_all", flavours=["all"])
    replace_day_stats(
        dbsession, day=date(2025, 12, 31), counts={_tf(title.id, "all"): 1}
    )
    replace_day_stats(dbsession, day=date(2026, 1, 1), counts={_tf(title.id, "all"): 2})

    assert get_downloads_for_flavour(
        dbsession,
        title_id=title.id,
        flavour="all",
        start=date(2025, 12, 30),
        end=date(2026, 1, 2),
    ) == {date(2025, 12, 31): 1, date(2026, 1, 1): 2}


def test_fetched_days_lifecycle(dbsession: OrmSession):
    start, end = date(2026, 1, 1), date(2026, 12, 31)
    assert get_fetched_days(dbsession, start=start, end=end) == set()

    mark_day_fetched(dbsession, day=date(2026, 10, 5), nb_downloads=10)
    assert get_fetched_days(dbsession, start=start, end=end) == {date(2026, 10, 5)}

    assert unmark_day_fetched(dbsession, day=date(2026, 10, 5)) is True
    assert unmark_day_fetched(dbsession, day=date(2026, 10, 5)) is False
    assert get_fetched_days(dbsession, start=start, end=end) == set()


def test_purge_old_stats(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    title = create_title(name="wikipedia_en_all", flavours=["all"])
    replace_day_stats(dbsession, day=date(2024, 5, 1), counts={_tf(title.id, "all"): 1})
    replace_day_stats(dbsession, day=date(2025, 5, 1), counts={_tf(title.id, "all"): 2})
    mark_day_fetched(dbsession, day=date(2024, 5, 1), nb_downloads=1)
    mark_day_fetched(dbsession, day=date(2025, 5, 1), nb_downloads=2)

    stats_deleted, fetch_deleted = purge_old_stats(dbsession, keep_since_year=2025)
    assert stats_deleted == 1
    assert fetch_deleted == 1

    assert (
        get_downloads_for_flavour(
            dbsession,
            title_id=title.id,
            flavour="all",
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
        )
        == {}
    )
    assert get_downloads_for_flavour(
        dbsession,
        title_id=title.id,
        flavour="all",
        start=date(2025, 1, 1),
        end=date(2025, 12, 31),
    ) == {date(2025, 5, 1): 2}
