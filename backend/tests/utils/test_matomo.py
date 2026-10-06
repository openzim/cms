from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from cms_backend.utils.matomo import (
    DOWNLOAD_STATS_PAGE_SIZE,
    fetch_download_stats_for_day,
)


def _mock_response(payload: object) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_fetch_filters_aggregates_and_skips_summary():
    payload = [
        {
            "label": "lb.download.kiwix.org/ - Others",
            "nb_visits": 81314,
            "nb_hits": 395391,
            "is_summary": True,
        },
        {
            "label": "lb.download.kiwix.org/zim/foo.zim",
            "url": "https://lb.download.kiwix.org/zim/foo.zim",
            "nb_hits": 3,
        },
        {
            "label": "lb.download.kiwix.org/zim/foo.zim.torrent",
            "url": "https://lb.download.kiwix.org/zim/foo.zim.torrent",
            "nb_hits": 2,
        },
        {
            "label": "lb.download.kiwix.org/zim/foo.zim.meta4",
            "url": "https://lb.download.kiwix.org/zim/foo.zim.meta4",
            "nb_hits": 1,
        },
        {
            "label": "lb.download.kiwix.org/zim/bar.zim",
            "url": "https://lb.download.kiwix.org/zim/bar.zim",
            "nb_hits": 4,
        },
        {
            "label": "lb.download.kiwix.org/index.html",
            "url": "https://lb.download.kiwix.org/index.html",
            "nb_hits": 10,
        },
    ]
    with patch(
        "cms_backend.utils.matomo.requests.post",
        return_value=_mock_response(payload),
    ) as mock_post:
        result = fetch_download_stats_for_day(date(2026, 10, 5))

    assert result == {
        ("lb.download.kiwix.org", "/zim/foo.zim"): 6,
        ("lb.download.kiwix.org", "/zim/bar.zim"): 4,
    }
    _, kwargs = mock_post.call_args
    assert kwargs["data"]["method"] == "Actions.getDownloads"
    assert kwargs["data"]["date"] == "2026-10-05"
    assert kwargs["data"]["filter_limit"] == DOWNLOAD_STATS_PAGE_SIZE
    assert kwargs["data"]["filter_offset"] == 0


def test_fetch_paginates_until_last_page(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("cms_backend.utils.matomo.DOWNLOAD_STATS_PAGE_SIZE", 2)
    pages = [
        _mock_response(
            [
                {"url": "https://lb.download.kiwix.org/zim/a.zim", "nb_hits": 1},
                {"url": "https://lb.download.kiwix.org/zim/b.zim", "nb_hits": 1},
            ]
        ),
        _mock_response(
            [{"url": "https://lb.download.kiwix.org/zim/c.zim", "nb_hits": 5}]
        ),
    ]
    with patch(
        "cms_backend.utils.matomo.requests.post", side_effect=pages
    ) as mock_post:
        result = fetch_download_stats_for_day(date(2026, 10, 5))

    assert mock_post.call_count == 2
    assert result == {
        ("lb.download.kiwix.org", "/zim/a.zim"): 1,
        ("lb.download.kiwix.org", "/zim/b.zim"): 1,
        ("lb.download.kiwix.org", "/zim/c.zim"): 5,
    }
    assert mock_post.call_args_list[0].kwargs["data"]["filter_offset"] == 0
    assert mock_post.call_args_list[1].kwargs["data"]["filter_offset"] == 2
