from datetime import date
from typing import Any, cast

import requests

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.utils.filename import DownloadLocation, normalize_download_location

DOWNLOAD_STATS_PAGE_SIZE = 1000

MAX_PAGES = 1000


def fetch_download_stats_for_day(day: date) -> dict[DownloadLocation, int]:
    """Fetch the lb.download.kiwix.org per-file download counts for day.

    Returns a mapping of normalized download location to the number of
    downloads (hits) for that location on the day. Torrent and meta4 downloads
    are folded into their matching `.zim` location.
    """
    page_size = DOWNLOAD_STATS_PAGE_SIZE
    downloads: dict[DownloadLocation, int] = {}
    offset = 0

    for _ in range(MAX_PAGES):
        rows = _fetch_downloads_page(day, limit=page_size, offset=offset)
        if not rows:
            break
        for row in rows:
            _accumulate_download(row, day=day, downloads=downloads)
        if len(rows) < page_size:
            break
        offset += page_size
    else:
        logger.warning(
            f"Stopped fetching download stats for {day} after {MAX_PAGES} pages"
        )

    logger.debug(f"Matomo returned {len(downloads)} download location(s) for {day}")
    return downloads


def _fetch_downloads_page(day: date, *, limit: int, offset: int) -> list[Any]:
    """Fetch a single page of the Matomo downloads report for day."""
    params: dict[str, Any] = {
        "module": "API",
        "method": "Actions.getDownloads",
        "idSite": Context.matomo_site_id,
        "period": "day",
        "date": day.isoformat(),
        "filter_limit": limit,
        "filter_offset": offset,
        "flat": 1,
        "format": "json",
    }

    response = requests.post(
        Context.matomo_url,
        data=params,
        timeout=Context.requests_timeout,
    )
    response.raise_for_status()
    return cast(list[Any], response.json())


def _accumulate_download(
    row: Any, *, day: date, downloads: dict[DownloadLocation, int]
) -> None:
    """Add a single Matomo report row to the accumulated downloads."""
    if not isinstance(row, dict):
        return
    row_data = cast(dict[str, Any], row)
    if row_data.get("is_summary"):
        logger.warning(
            f"Matomo returned summary row for {day}; downloads "
            "from that bucket cannot be attributed to a flavour"
        )
        return
    url = _get_download_url(row_data)
    if url is None:
        return
    location = normalize_download_location(url)
    if location is None:
        return
    hits = _get_hits(row_data)
    if hits <= 0:
        return
    downloads[location] = downloads.get(location, 0) + hits


def _get_download_url(row: dict[str, Any]) -> str | None:
    """Return the download URL of a Matomo row.

    The full URL is exposed in the url field while label may omit the
    scheme, so url is preferred.
    """
    for key in ("url", "label"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _get_hits(row: dict[str, Any]) -> int:
    """Extract the download count from a Matomo report row."""
    for key in ("nb_hits", "nb_visits"):
        value = row.get(key)
        if value is None:
            continue
        return int(value)
    return 0
