from http import HTTPStatus
from typing import Any

import pytest

from cms_backend.api.context import Context as ApiContext
from cms_backend.utils.github import (
    GitHubClient,
    PublicationRepository,
    PublicationResult,
    get_repository_config,
)
from cms_backend.utils.requests import Response


def _response(status_code: int, payload: dict[str, Any] | None = None) -> Response:
    return Response(
        status_code=status_code,
        success=200 <= status_code < 300,
        json=payload or {},
    )


@pytest.fixture(autouse=True)
def github_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ApiContext, "github_token", "test-token")
    monkeypatch.setattr(ApiContext, "github_api_url", "https://api.github.test")
    monkeypatch.setattr(
        ApiContext, "github_android_repo", "kiwix/kiwix-android-branded"
    )
    monkeypatch.setattr(ApiContext, "github_android_workflow", "cd.yml")
    monkeypatch.setattr(ApiContext, "github_android_branch", "main")
    monkeypatch.setattr(ApiContext, "github_apple_repo", "")
    monkeypatch.setattr(ApiContext, "github_apple_workflow", "cd.yml")
    monkeypatch.setattr(ApiContext, "github_apple_branch", "main")


def test_get_repository_config_android() -> None:
    assert get_repository_config("android") == PublicationRepository(
        repo="kiwix/kiwix-android-branded", workflow="cd.yml", branch="main"
    )


def test_get_repository_config_apple_not_configured() -> None:
    with pytest.raises(ValueError, match="not configured"):
        get_repository_config("apple")


def test_get_repository_config_unknown_store() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        get_repository_config("windows")


def test_publish_creates_tag_then_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tags: list[str] = []

    def fake_query_api(url: str, method: str = "get", **kwargs: Any) -> Response:
        if method.upper() == "GET" and url.endswith("/commits/main"):
            return _response(HTTPStatus.OK, {"sha": "deadbeef"})
        if method.upper() == "POST" and url.endswith("/git/refs"):
            tags.append(kwargs["payload"]["ref"])
            return _response(HTTPStatus.CREATED)
        if method.upper() == "POST" and url.endswith("/releases"):
            return _response(
                HTTPStatus.CREATED,
                {"id": 42, "html_url": "https://github.test/release/42"},
            )
        raise AssertionError(f"Unexpected call: {method} {url}")

    monkeypatch.setattr("cms_backend.utils.github.query_api", fake_query_api)

    result = GitHubClient().publish(
        store="android", app_name="phet", content_version="2026-05"
    )

    assert result == PublicationResult(
        tag="phet_2026.05.0",
        commit_sha="deadbeef",
        release_id=42,
        release_url="https://github.test/release/42",
        repository="kiwix/kiwix-android-branded",
        workflow="cd.yml",
    )
    assert tags == ["refs/tags/phet_2026.05.0"]


def test_publish_increments_build_number_when_tag_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tags: list[str] = []
    tag_attempts = 0

    def fake_query_api(url: str, method: str = "get", **kwargs: Any) -> Response:
        nonlocal tag_attempts
        if method.upper() == "GET" and url.endswith("/commits/main"):
            return _response(HTTPStatus.OK, {"sha": "abc"})
        if method.upper() == "POST" and url.endswith("/git/refs"):
            tag_attempts += 1
            tags.append(kwargs["payload"]["ref"])
            if tag_attempts == 1:
                return _response(HTTPStatus.UNPROCESSABLE_ENTITY)
            return _response(HTTPStatus.CREATED)
        if method.upper() == "POST" and url.endswith("/releases"):
            return _response(
                HTTPStatus.CREATED,
                {"id": 1, "html_url": "https://github.test/release/1"},
            )
        raise AssertionError(f"Unexpected call: {method} {url}")

    monkeypatch.setattr("cms_backend.utils.github.query_api", fake_query_api)

    result = GitHubClient().publish(
        store="android", app_name="phet", content_version="2026-05"
    )

    assert result.tag == "phet_2026.05.1"
    assert tag_attempts == 2
    assert tags == [
        "refs/tags/phet_2026.05.0",
        "refs/tags/phet_2026.05.1",
    ]
