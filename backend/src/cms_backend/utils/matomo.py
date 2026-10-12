from datetime import date
from typing import Any, cast

import requests

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.utils.filename import DownloadLocation, normalize_download_location

# Number of visits fetched per Matomo request.
DOWNLOAD_STATS_PAGE_SIZE = 500

# Safety net against a server ignoring ``filter_offset`` and looping forever.
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
        visits = _fetch_visits_page(day, limit=page_size, offset=offset)
        if not visits:
            break
        for visit in visits:
            _accumulate_visit(visit, downloads=downloads)
        offset += len(visits)
    else:
        logger.warning(
            f"Stopped fetching download stats for {day} after {MAX_PAGES} pages"
        )

    logger.debug(f"Matomo returned {len(downloads)} download location(s) for {day}")
    return downloads


def _fetch_visits_page(day: date, *, limit: int, offset: int) -> list[Any]:
    """Fetch a single page of the Matomo downloads Live report for day."""
    params: dict[str, Any] = {
        "module": "API",
        "method": "Live.getLastVisitsDetails",
        "idSite": Context.matomo_site_id,
        "period": "day",
        "date": day.isoformat(),
        "segment": "actionType==downloads",
        "filter_limit": limit,
        "filter_offset": offset,
        "format": "json",
    }

    response = requests.post(
        Context.matomo_url,
        data=params,
        timeout=Context.requests_timeout,
    )
    response.raise_for_status()

    payload = response.json()
    if isinstance(payload, dict):
        payload_dict = cast(dict[str, Any], payload)
        if payload_dict.get("result") == "error":
            raise ValueError(f"Matomo API error: {payload_dict.get('message')}")
        return list(payload_dict.values())
    if isinstance(payload, list):
        return cast(list[Any], payload)
    return []


def _accumulate_visit(visit: Any, *, downloads: dict[DownloadLocation, int]) -> None:
    """Add the download actions of a single Matomo visit to ``downloads``."""
    if not isinstance(visit, dict):
        return
    visit_data = cast(dict[str, Any], visit)
    action_details = visit_data.get("actionDetails")
    if not isinstance(action_details, list):
        return
    for action in cast(list[Any], action_details):
        if not isinstance(action, dict):
            continue
        action_data = cast(dict[str, Any], action)
        if action_data.get("type") != "download":
            continue
        url = action_data.get("url")
        if not isinstance(url, str) or not url:
            continue
        location = normalize_download_location(url)
        if location is None:
            continue
        downloads[location] = downloads.get(location, 0) + 1
