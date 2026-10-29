import base64
import json
from http import HTTPStatus
from typing import Any

import pytest

from cms_backend.context import Context
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
    monkeypatch.setattr(Context, "github_token", "test-token")
    monkeypatch.setattr(Context, "github_api_url", "https://api.github.test")
    monkeypatch.setattr(Context, "github_android_repo", "kiwix/kiwix-android-branded")
    monkeypatch.setattr(Context, "github_android_workflow", "cd.yml")
    monkeypatch.setattr(Context, "github_android_branch", "main")
    monkeypatch.setattr(Context, "github_apple_repo", "")
    monkeypatch.setattr(Context, "github_apple_workflow", "cd.yml")
    monkeypatch.setattr(Context, "github_apple_branch", "main")


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


def _info_json(zim_filename: str) -> str:
    return (
        "{\n"
        '  "app_name": "PhET",\n'
        '  "zim_url": "https://lb.download.kiwix.org/zim/phet/'
        f'{zim_filename}"\n'
        "}\n"
    )


def test_create_publication_pull_request_replaces_only_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _info_json("phet_mul_all_2026-05.zim")
    put_payloads: list[dict[str, Any]] = []

    def fake_query_api(url: str, method: str = "get", **kwargs: Any) -> Response:
        if method.upper() == "GET" and url.endswith("/commits/main"):
            return _response(HTTPStatus.OK, {"sha": "base-sha"})
        if method.upper() == "GET" and url.endswith("/contents/phet/info.json"):
            return _response(
                HTTPStatus.OK,
                {
                    "content": base64.b64encode(current.encode()).decode(),
                    "sha": "file-sha",
                },
            )
        if method.upper() == "POST" and url.endswith("/git/refs"):
            return _response(HTTPStatus.CREATED)
        if method.upper() == "PUT" and url.endswith("/contents/phet/info.json"):
            put_payloads.append(kwargs["payload"])
            return _response(HTTPStatus.OK)
        if method.upper() == "GET" and url.endswith("/pulls"):
            return _response(HTTPStatus.OK, {})
        if method.upper() == "POST" and url.endswith("/pulls"):
            return _response(
                HTTPStatus.CREATED,
                {
                    "number": 7,
                    "html_url": "https://github.test/pull/7",
                },
            )
        raise AssertionError(f"Unexpected call: {method} {url}")

    monkeypatch.setattr("cms_backend.utils.github.query_api", fake_query_api)

    result = GitHubClient().create_publication_pull_request(
        store="android",
        app_name="phet",
        content_version="2026-08",
        zim_filename="phet_mul_all_2026-08.zim",
        branch="cms/publication-test",
        publication_id="publication-id",
    )

    assert result.base_sha == "base-sha"
    assert result.pr_number == 7
    assert len(put_payloads) == 1
    assert put_payloads[0]["sha"] == "file-sha"
    updated = json.loads(base64.b64decode(put_payloads[0]["content"]).decode())
    assert updated["zim_url"] == (
        "https://lb.download.kiwix.org/zim/phet/phet_mul_all_2026-08.zim"
    )


def test_create_publication_pull_request_skips_when_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _info_json("phet_mul_all_2026-08.zim")

    def fake_query_api(url: str, method: str = "get", **_kwargs: Any) -> Response:
        if method.upper() == "GET" and url.endswith("/commits/main"):
            return _response(HTTPStatus.OK, {"sha": "base-sha"})
        if method.upper() == "GET" and url.endswith("/contents/phet/info.json"):
            return _response(
                HTTPStatus.OK,
                {"content": base64.b64encode(current.encode()).decode()},
            )
        raise AssertionError(f"Unexpected call: {method} {url}")

    monkeypatch.setattr("cms_backend.utils.github.query_api", fake_query_api)

    result = GitHubClient().create_publication_pull_request(
        store="android",
        app_name="phet",
        content_version="2026-08",
        zim_filename="phet_mul_all_2026-08.zim",
        branch="cms/publication-test",
        publication_id="publication-id",
    )

    assert result.base_sha == "base-sha"
    assert result.branch == "main"
    assert result.pr_number is None
    assert result.pr_url is None


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
