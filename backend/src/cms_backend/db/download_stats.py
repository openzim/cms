from datetime import date, timedelta
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    DownloadStats,
    DownloadStatsFetch,
    Title,
)
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import (
    DownloadLocation,
    construct_download_url,
    normalize_download_location,
)


class TitleFlavourKey(NamedTuple):
    title_id: UUID
    flavour: str


def _day_of_year(day: date) -> int:
    """Return the 1-based day of year of day (1..366)."""
    return day.timetuple().tm_yday


def _date_from_day_of_year(year: int, day_of_year: int) -> date | None:
    """Return the date matching day_of_year for year.

    Returns None for slot 366 of a non-leap year (which does not exist).
    """
    day = date(year, 1, 1) + timedelta(days=day_of_year - 1)
    if day.year != year:
        return None
    return day


def get_prod_download_location_map(
    session: OrmSession,
) -> dict[DownloadLocation, TitleFlavourKey]:
    """Map download locations to their (title_id, flavour)."""
    stmt = (
        select(
            Book.title_id,
            Book.flavour,
            Collection.download_base_url,
            CollectionTitle.path,
            BookLocation.filename,
        )
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle, CollectionTitle.title_id == Title.id)
        .join(Collection, Collection.id == CollectionTitle.collection_id)
        .join(
            BookLocation,
            and_(
                BookLocation.book_id == Book.id,
                BookLocation.status == "current",
                BookLocation.warehouse_id == Collection.warehouse_id,
                BookLocation.path == CollectionTitle.path,
                BookLocation.is_backup.is_not(True),
            ),
        )
        .where(
            Book.location_kind == "prod",
            Book.needs_processing.is_(False),
            Book.has_error.is_(False),
            Book.needs_file_operation.is_(False),
            Book.filename.is_not(None),
            Collection.download_base_url.is_not(None),
        )
    )

    result: dict[DownloadLocation, TitleFlavourKey] = {}
    for row in session.execute(stmt).all():
        location = normalize_download_location(
            construct_download_url(row.download_base_url, row.path, row.filename)
        )
        if location is None:
            continue
        value = TitleFlavourKey(title_id=row.title_id, flavour=row.flavour)
        existing = result.get(location)
        if existing is not None and existing != value:
            logger.warning(
                f"Download location {location} maps to both {existing} and "
                f"{value}, keeping the first one"
            )
            continue
        result[location] = value
    return result


def replace_day_stats(
    session: OrmSession,
    *,
    day: date,
    counts: dict[TitleFlavourKey, int],
) -> int:
    """Replace all download statistics for day with counts.

    Existing values for that day are cleared first so that flavours which had
    downloads before but not anymore are reset. Only positive counts are stored
    (a NULL slot means "no downloads"). Returns the total number of
    downloads stored.
    """
    year = day.year
    slot = _day_of_year(day) - 1

    rows = {
        TitleFlavourKey(title_id=row.title_id, flavour=row.flavour): row
        for row in session.scalars(
            select(DownloadStats).where(DownloadStats.year == year)
        )
    }
    for row in rows.values():
        if row.lb_downloads[slot] is not None:
            row.lb_downloads[slot] = None

    total = 0
    for title_flavour, count in counts.items():
        if count <= 0:
            continue
        row = rows.get(title_flavour)
        if row is None:
            lb_downloads: list[int | None] = [None] * 366
            lb_downloads[slot] = count
            row = DownloadStats(
                title_id=title_flavour.title_id,
                flavour=title_flavour.flavour,
                year=year,
                lb_downloads=lb_downloads,
            )
            session.add(row)
            rows[title_flavour] = row
        else:
            row.lb_downloads[slot] = count
        total += count

    session.flush()
    return total


def get_fetched_days(session: OrmSession, *, start: date, end: date) -> set[date]:
    """Return the set of days already fetched within [start, end]."""
    return set(
        session.scalars(
            select(DownloadStatsFetch.day).where(
                DownloadStatsFetch.day >= start,
                DownloadStatsFetch.day <= end,
            )
        ).all()
    )


def mark_day_fetched(
    session: OrmSession, *, day: date, nb_downloads: int
) -> DownloadStatsFetch:
    """Record that day has been fetched to completion."""
    entry = session.get(DownloadStatsFetch, day)
    if entry is None:
        entry = DownloadStatsFetch(day=day, nb_downloads=nb_downloads)
        session.add(entry)
    else:
        entry.fetched_at = getnow()
        entry.nb_downloads = nb_downloads
    session.flush()
    return entry


def unmark_day_fetched(session: OrmSession, *, day: date) -> bool:
    """Forget that day was fetched, forcing a refetch. Returns True if a day
    was actually removed."""
    result = session.execute(
        delete(DownloadStatsFetch).where(DownloadStatsFetch.day == day)
    )
    session.flush()
    return bool(result.rowcount)


def purge_old_stats(session: OrmSession, *, keep_since_year: int) -> tuple[int, int]:
    """Delete statistics older than keep_since_year.

    Returns the number of (stats rows, fetched-days rows) deleted.
    """
    stats_deleted = session.execute(
        delete(DownloadStats).where(DownloadStats.year < keep_since_year)
    ).rowcount
    fetch_deleted = session.execute(
        delete(DownloadStatsFetch).where(
            DownloadStatsFetch.day < date(keep_since_year, 1, 1)
        )
    ).rowcount
    session.flush()
    return stats_deleted, fetch_deleted


def get_downloads_for_flavour(
    session: OrmSession,
    *,
    title_id: UUID,
    flavour: str,
    start: date,
    end: date,
) -> dict[date, int]:
    """Return the daily downloads of a title flavour within [start, end].

    Only days with at least one download are present in the result.
    """
    years = list(range(start.year, end.year + 1))
    rows = session.scalars(
        select(DownloadStats).where(
            DownloadStats.title_id == title_id,
            DownloadStats.flavour == flavour,
            DownloadStats.year.in_(years),
        )
    ).all()

    downloads: dict[date, int] = {}
    for row in rows:
        for slot, value in enumerate(row.lb_downloads, start=1):
            if value is None:
                continue
            day = _date_from_day_of_year(row.year, slot)
            if day is None or not (start <= day <= end):
                continue
            downloads[day] = value
    return downloads
