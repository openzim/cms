from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import DownloadStats, DownloadStatsFetch, Title

MIN_POPULARITY = 1
MAX_POPULARITY = 100


def compute_titles_popularity(session: OrmSession, *, lookback_days: int) -> int:
    """Recompute and store the popularity of every title.

    Returns the number of titles whose popularity were updated.
    """
    fetched_days = session.scalars(
        select(DownloadStatsFetch.day)
        .order_by(DownloadStatsFetch.day.desc())
        .limit(lookback_days)
    ).all()
    if not fetched_days:
        logger.info("No download statistics available, skipping popularity update")
        return 0

    # day-of-year slots (0-based) to sum, grouped by year
    slots_by_year: dict[int, list[int]] = defaultdict(list)
    for day in fetched_days:
        slots_by_year[day.year].append(day.timetuple().tm_yday - 1)

    # Mapping of each title to it's total download stats
    totals: dict[UUID, int] = defaultdict(int)
    stats = session.scalars(
        select(DownloadStats).where(DownloadStats.year.in_(list(slots_by_year)))
    )
    for stat in stats:
        for slot in slots_by_year.get(stat.year, []):
            value = stat.lb_downloads[slot]
            if value is not None:
                totals[stat.title_id] += value

    if not any(totals.values()):
        logger.info("No downloads in the popularity window, skipping update")
        return 0

    title_ids = session.scalars(select(Title.id)).all()
    if not title_ids:
        return 0

    ranked = sorted(
        title_ids, key=lambda title_id: totals.get(title_id, 0), reverse=True
    )
    total = len(ranked)
    updated = 0
    previous_value: int | None = None
    greater_count = 0
    for index, title_id in enumerate(ranked):
        title = session.scalars(select(Title).where(Title.id == title_id)).one()
        value = totals.get(title.id, 0)
        if value != previous_value:
            # number of titles with strictly more downloads
            greater_count = index
            previous_value = value

        popularity = MAX_POPULARITY - (greater_count * MAX_POPULARITY) // total
        popularity = max(MIN_POPULARITY, min(MAX_POPULARITY, popularity))
        if title.popularity != popularity:
            title.popularity = popularity
            updated += 1

    session.flush()
    logger.info(f"Recomputed popularity for {updated} title(s)")
    return updated
