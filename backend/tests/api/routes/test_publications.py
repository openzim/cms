from collections.abc import Callable
from http import HTTPStatus
from typing import Any

import pytest
from fastapi.testclient import TestClient

from cms_backend.api.context import Context as ApiContext
from cms_backend.db.models import Application, ApplicationPublication, Book, Title
from cms_backend.utils.github import PublicationResult, github_client


def test_create_publication(
    client: TestClient,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ApiContext, "publication_stores", ["android"])

    title = create_title(name="phet_mul_all", flavours=["maxi"])
    create_application(
        title=title, flavour="maxi", store="android", name="phet", enabled=True
    )
    create_book(
        title_id=title.id,
        flavour="maxi",
        filename="phet_mul_all_maxi_2026-05.zim",
        location_kind="prod",
        date="2026-05-01",
    )

    def fake_publish(**_kwargs: Any) -> PublicationResult:
        return PublicationResult(
            tag="phet_2026.05.0",
            commit_sha="abc",
            release_id=1,
            release_url="https://github.test/release/1",
            repository="kiwix/kiwix-android-branded",
            workflow="cd.yml",
        )

    monkeypatch.setattr(github_client, "publish", fake_publish)

    response = client.post(
        "/v1/publications",
        json={
            "title_identifier": str(title.id),
            "flavour": "maxi",
            "store": "android",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["store"] == "android"
    assert data["content_version"] == "2026-05"
    assert data["tag"] == "phet_2026.05.0"
    assert data["status"] == "pending"
    assert data["repository"] == "kiwix/kiwix-android-branded"


def test_create_publication_disabled(
    client: TestClient,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ApiContext, "publication_stores", ["android"])

    title = create_title(name="phet_mul_all", flavours=["maxi"])
    create_application(
        title=title, flavour="maxi", store="android", name="phet", enabled=False
    )
    create_book(
        title_id=title.id,
        flavour="maxi",
        filename="phet_mul_all_maxi_2026-05.zim",
        location_kind="prod",
        date="2026-05-01",
    )

    response = client.post(
        "/v1/publications",
        json={
            "title_identifier": str(title.id),
            "flavour": "maxi",
            "store": "android",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_create_publication_store_not_enabled(
    client: TestClient,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ApiContext, "publication_stores", ["android"])

    title = create_title(name="phet_mul_all", flavours=["maxi"])
    create_application(
        title=title, flavour="maxi", store="apple", name="phet", enabled=True
    )
    create_book(
        title_id=title.id,
        flavour="maxi",
        filename="phet_mul_all_maxi_2026-05.zim",
        location_kind="prod",
        date="2026-05-01",
    )

    response = client.post(
        "/v1/publications",
        json={
            "title_identifier": str(title.id),
            "flavour": "maxi",
            "store": "apple",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_create_publication_without_book(
    client: TestClient,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ApiContext, "publication_stores", ["android"])

    title = create_title(name="phet_mul_all", flavours=["maxi"])
    create_application(
        title=title, flavour="maxi", store="android", name="phet", enabled=True
    )

    response = client.post(
        "/v1/publications",
        json={
            "title_identifier": str(title.id),
            "flavour": "maxi",
            "store": "android",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.parametrize(
    ("name", "store", "expected_status", "expected_count", "expected_tags"),
    [
        pytest.param(
            "phet",
            "android",
            HTTPStatus.OK,
            1,
            ["phet_2026.05.0"],
            id="phet-android",
        ),
        pytest.param(
            "phet2",
            "android",
            HTTPStatus.OK,
            1,
            ["phet2_2026.05.0"],
            id="phet2-android",
        ),
        pytest.param(
            "wikipedia",
            "apple",
            HTTPStatus.OK,
            1,
            ["wikipedia_2026.05.0"],
            id="wikipedia-apple",
        ),
        pytest.param(
            "wikipedia",
            "android",
            HTTPStatus.NOT_FOUND,
            None,
            None,
            id="wrong-store",
        ),
        pytest.param(
            "unknown",
            "android",
            HTTPStatus.NOT_FOUND,
            None,
            None,
            id="unknown-application",
        ),
    ],
)
def test_list_publications(
    client: TestClient,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    create_publication: Callable[..., ApplicationPublication],
    access_token: str,
    name: str,
    store: str,
    expected_status: HTTPStatus,
    expected_count: int | None,
    expected_tags: list[str] | None,
) -> None:
    phet_title = create_title(name="phet_mul_all", flavours=["maxi", "mini"])
    wikipedia_title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    create_application(title=phet_title, flavour="maxi", store="android", name="phet")
    create_application(title=phet_title, flavour="mini", store="android", name="phet2")
    create_application(
        title=wikipedia_title, flavour="maxi", store="apple", name="wikipedia"
    )
    create_publication(
        title=phet_title, flavour="maxi", store="android", app_name="phet"
    )
    create_publication(
        title=phet_title, flavour="mini", store="android", app_name="phet2"
    )
    create_publication(
        title=wikipedia_title, flavour="maxi", store="apple", app_name="wikipedia"
    )

    response = client.get(
        "/v1/publications",
        params={"name": name, "store": store},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == expected_status
    if expected_count is not None:
        data = response.json()
        assert data["meta"]["count"] == expected_count
        assert len(data["items"]) == expected_count
        if expected_tags is not None:
            assert [item["tag"] for item in data["items"]] == expected_tags


def test_get_publication_refreshes_status(
    client: TestClient,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    create_publication: Callable[..., ApplicationPublication],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    title = create_title(name="phet_mul_all", flavours=["maxi"])
    create_application(
        title=title, flavour="maxi", store="android", name="phet", enabled=True
    )
    publication = create_publication(
        title=title, flavour="maxi", store="android", app_name="phet"
    )

    def fake_get_run(**_kwargs: Any) -> dict[str, Any]:
        return {
            "id": 7,
            "html_url": "https://github.test/run/7",
            "status": "completed",
            "conclusion": "success",
        }

    monkeypatch.setattr(github_client, "get_run_for_publication", fake_get_run)

    response = client.get(
        f"/v1/publications/{publication.id}",
        params={"name": "phet", "store": "android"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "success"
    assert data["run_url"] == "https://github.test/run/7"
