"""Tests for the title popularity computation."""

from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.download_stats import (
    TitleFlavourKey,
    mark_day_fetched,
    replace_day_stats,
)
from cms_backend.db.models import Title
from cms_backend.db.popularity import compute_titles_popularity


def _tf(title: Title, flavour: str = "all") -> TitleFlavourKey:
    return TitleFlavourKey(title_id=title.id, flavour=flavour)


def test_compute_popularity_ranks_and_buckets(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    t1 = create_title(name="t1", flavours=["all"])
    t2 = create_title(name="t2", flavours=["all"])
    t3 = create_title(name="t3", flavours=["all"])
    t4 = create_title(name="t4", flavours=["all"])
    day = date(2026, 10, 5)
    replace_day_stats(
        dbsession,
        day=day,
        counts={_tf(t1): 10, _tf(t2): 10, _tf(t3): 5, _tf(t4): 0},
    )
    mark_day_fetched(dbsession, day=day, nb_downloads=25)

    updated = compute_titles_popularity(dbsession, lookback_days=7)

    assert updated == 4
    assert t1.popularity == 100
    assert t2.popularity == 100  # tie shares the same popularity
    assert t3.popularity == 50
    assert t4.popularity == 25


def test_compute_popularity_sums_over_flavours(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    t1 = create_title(name="t1", flavours=["all", "maxi"])
    t2 = create_title(name="t2", flavours=["all"])
    day = date(2026, 10, 5)
    replace_day_stats(
        dbsession,
        day=day,
        counts={
            _tf(t1, "all"): 3,
            _tf(t1, "maxi"): 4,
            _tf(t2, "all"): 5,
        },
    )
    mark_day_fetched(dbsession, day=day, nb_downloads=12)

    compute_titles_popularity(dbsession, lookback_days=7)

    # t1 total = 7, t2 total = 5
    assert t1.popularity == 100
    assert t2.popularity == 50


def test_compute_popularity_uses_latest_days(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    t1 = create_title(name="t1", flavours=["all"])
    t2 = create_title(name="t2", flavours=["all"])
    old_day = date(2026, 10, 4)
    new_day = date(2026, 10, 5)

    replace_day_stats(dbsession, day=old_day, counts={_tf(t1): 100, _tf(t2): 1})
    mark_day_fetched(dbsession, day=old_day, nb_downloads=101)
    replace_day_stats(dbsession, day=new_day, counts={_tf(t1): 1, _tf(t2): 100})

    mark_day_fetched(dbsession, day=new_day, nb_downloads=101)

    # only the most recent day is considered
    compute_titles_popularity(dbsession, lookback_days=1)

    assert t1.popularity == 50
    assert t2.popularity == 100
