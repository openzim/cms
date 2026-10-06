"""Tests for the Matomo download statistics client."""

from datetime import date
from typing import Any
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


def _visit(*urls: str, action_type: str = "download") -> dict[str, Any]:
    return {
        "actionDetails": [{"type": action_type, "url": url} for url in urls],
    }


def test_fetch_counts_download_actions_and_folds_extensions():
    payload = [
        # a pageview before the download must be ignored
        {
            "actionDetails": [
                {"type": "pageview", "url": "https://lb.download.kiwix.org/"},
                {
                    "type": "download",
                    "url": "https://lb.download.kiwix.org/zim/foo.zim",
                },
            ]
        },
        _visit(
            "https://lb.download.kiwix.org/zim/foo.zim.torrent",
            "https://lb.download.kiwix.org/zim/foo.zim.meta4",
        ),
        _visit(
            "https://lb.download.kiwix.org/zim/bar.zim",
            # not a ZIM download, must be ignored
            "https://lb.download.kiwix.org/index.html",
        ),
    ]
    with patch(
        "cms_backend.utils.matomo.requests.post",
        side_effect=[_mock_response(payload), _mock_response([])],
    ) as mock_post:
        result = fetch_download_stats_for_day(date(2026, 10, 5))

    assert result == {
        ("lb.download.kiwix.org", "/zim/foo.zim"): 3,
        ("lb.download.kiwix.org", "/zim/bar.zim"): 1,
    }
    first_call = mock_post.call_args_list[0]
    assert first_call.kwargs["data"]["method"] == "Live.getLastVisitsDetails"
    assert first_call.kwargs["data"]["segment"] == "actionType==downloads"
    assert first_call.kwargs["data"]["filter_limit"] == DOWNLOAD_STATS_PAGE_SIZE
    assert first_call.kwargs["data"]["filter_offset"] == 0


def test_fetch_paginates_until_empty_page(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("cms_backend.utils.matomo.DOWNLOAD_STATS_PAGE_SIZE", 2)
    pages = [
        _mock_response(
            [
                _visit("https://lb.download.kiwix.org/zim/a.zim"),
                _visit("https://lb.download.kiwix.org/zim/b.zim"),
            ]
        ),
        _mock_response([_visit("https://lb.download.kiwix.org/zim/c.zim")]),
        _mock_response([]),
    ]
    with patch(
        "cms_backend.utils.matomo.requests.post", side_effect=pages
    ) as mock_post:
        result = fetch_download_stats_for_day(date(2026, 10, 5))

    assert mock_post.call_count == 3
    assert result == {
        ("lb.download.kiwix.org", "/zim/a.zim"): 1,
        ("lb.download.kiwix.org", "/zim/b.zim"): 1,
        ("lb.download.kiwix.org", "/zim/c.zim"): 1,
    }
    # the offset advances by the number of visits actually returned
    assert mock_post.call_args_list[0].kwargs["data"]["filter_offset"] == 0
    assert mock_post.call_args_list[1].kwargs["data"]["filter_offset"] == 2
    assert mock_post.call_args_list[2].kwargs["data"]["filter_offset"] == 3


def test_fetch_ignores_visits_without_download_actions():
    payload: list[Any] = [
        {"actionDetails": [{"type": "pageview", "url": "https://example.com"}]},
        {},
        {"actionDetails": []},
    ]
    with patch(
        "cms_backend.utils.matomo.requests.post",
        side_effect=[_mock_response(payload), _mock_response([])],
    ):
        result = fetch_download_stats_for_day(date(2026, 10, 5))

    assert result == {}


def test_fetch_raises_on_api_error():
    payload = {"result": "error", "message": "Invalid token_auth"}
    with patch(
        "cms_backend.utils.matomo.requests.post",
        return_value=_mock_response(payload),
    ):
        with pytest.raises(ValueError, match="Invalid token_auth"):
            fetch_download_stats_for_day(date(2026, 10, 5))
