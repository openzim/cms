from datetime import date, timedelta
from time import sleep

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db.download_stats import (
    TitleFlavourKey,
    get_fetched_days,
    get_prod_download_location_map,
    mark_day_fetched,
    purge_old_stats,
    replace_day_stats,
)
from cms_backend.mill.context import Context as MillContext
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import DownloadLocation
from cms_backend.utils.matomo import fetch_download_stats_for_day


def fetch_download_stats(session: OrmSession) -> None:
    """Fetch and store every missing lb.download.kiwix.org daily statistic."""
    now = getnow()
    today = now.date()
    start = today - timedelta(days=Context.download_stats_days_ago)
    end = today - timedelta(days=1)
    if now.hour < Context.download_stats_yesterday_hour:
        # yesterday statistics are only available after the configured hour
        end -= timedelta(days=1)

    if end >= start:
        _fetch_missing_days(session, start=start, end=end)
    else:
        logger.info("No day eligible for download stats fetching")

    _purge_old_stats(session)


def _fetch_missing_days(session: OrmSession, *, start: date, end: date) -> None:
    fetched_days = get_fetched_days(session, start=start, end=end)
    missing: list[date] = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        if day not in fetched_days:
            missing.append(day)

    if not missing:
        logger.info("No missing day to fetch for lb download stats")
        return

    location_map = get_prod_download_location_map(session)
    logger.info(
        f"Fetching download stats for {len(missing)} missing day(s), "
        f"{len(location_map)} known download location(s)"
    )
    for index, day in enumerate(missing):
        if index:
            sleep(MillContext.download_stats_request_delay)
        _fetch_day(session, day=day, location_map=location_map)


def _fetch_day(
    session: OrmSession,
    *,
    day: date,
    location_map: dict[DownloadLocation, TitleFlavourKey],
) -> None:
    logger.debug(f"Fetching download stats for {day}")
    try:
        path_downloads = fetch_download_stats_for_day(day)
    except Exception:
        logger.exception(f"Failed to fetch download stats for {day}")
        return

    counts: dict[TitleFlavourKey, int] = {}
    unmapped = 0
    for location, nb_downloads in path_downloads.items():
        mapping = location_map.get(location)
        if mapping is None:
            unmapped += nb_downloads
            continue
        counts[mapping] = counts.get(mapping, 0) + nb_downloads

    try:
        total = replace_day_stats(session, day=day, counts=counts)
        mark_day_fetched(session, day=day, nb_downloads=total)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception(f"Failed to store download stats for {day}")
        return

    logger.info(
        f"Stored download stats for {day}: {total} download(s) across "
        f"{len(counts)} flavour(s), {unmapped} unmapped download(s)"
    )


def _purge_old_stats(session: OrmSession) -> None:
    # Keep the whole current year and the whole previous year
    keep_since_year = getnow().year - 1
    try:
        stats_deleted, fetch_deleted = purge_old_stats(
            session, keep_since_year=keep_since_year
        )
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to purge old lb download stats")
        return

    if stats_deleted or fetch_deleted:
        logger.info(
            f"Purged {stats_deleted} download stats row(s) and "
            f"{fetch_deleted} fetched-day row(s) older than {keep_since_year}"
        )
