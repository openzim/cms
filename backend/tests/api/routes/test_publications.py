from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.context import Context
from cms_backend.db.collection_permission import create_collection_permission
from cms_backend.db.models import (
    Account,
    Application,
    ApplicationPublication,
    Book,
    Collection,
    Title,
)
from cms_backend.db.publication_permission import create_publication_permission
from cms_backend.roles import RoleEnum
from cms_backend.utils.datetime import getnow


def test_create_publication(
    client: TestClient,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Context, "publication_stores", ["android"])

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
    assert data["tag"] is None
    assert data["status"] == "pending"
    assert data["phase"] == "requested"
    assert data["repository"] == "kiwix/kiwix-android-branded"
    assert len(data["events"]) == 1
    assert "Publication requested" in data["events"][0]


def test_create_publication_rejects_active_publication(
    client: TestClient,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    create_publication: Callable[..., ApplicationPublication],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Context, "publication_stores", ["android"])

    title = create_title(name="phet_mul_all", flavours=["maxi"])
    application = create_application(
        title=title, flavour="maxi", store="android", name="phet", enabled=True
    )
    create_book(
        title_id=title.id,
        flavour="maxi",
        filename="phet_mul_all_maxi_2026-05.zim",
        location_kind="prod",
        date="2026-05-01",
    )
    create_publication(application=application)

    response = client.post(
        "/v1/publications",
        json={
            "title_identifier": str(title.id),
            "flavour": "maxi",
            "store": "android",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.CONFLICT


def test_create_publication_disabled(
    client: TestClient,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    access_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Context, "publication_stores", ["android"])

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
    monkeypatch.setattr(Context, "publication_stores", ["android"])

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
    monkeypatch.setattr(Context, "publication_stores", ["android"])

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
    phet_maxi = create_application(
        title=phet_title, flavour="maxi", store="android", name="phet"
    )
    phet_mini = create_application(
        title=phet_title, flavour="mini", store="android", name="phet2"
    )
    wikipedia_apple = create_application(
        title=wikipedia_title, flavour="maxi", store="apple", name="wikipedia"
    )
    create_publication(application=phet_maxi)
    create_publication(application=phet_mini)
    create_publication(application=wikipedia_apple)

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


def test_cancel_publication(
    client: TestClient,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    create_publication: Callable[..., ApplicationPublication],
    account: Account,
    access_token: str,
) -> None:
    title = create_title(name="phet_mul_all", flavours=["maxi"])
    application = create_application(
        title=title, flavour="maxi", store="android", name="phet", enabled=True
    )
    publication = create_publication(
        application=application,
        status="running",
        phase="checks",
    )

    response = client.post(
        f"/v1/publications/{publication.id}/cancel",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["phase"] is None
    assert data["cancelled_by"] == account.display_name
    assert f"cancelled by {account.display_name}" in data["events"][-1]


def test_cancel_finished_publication(
    client: TestClient,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    create_publication: Callable[..., ApplicationPublication],
    access_token: str,
) -> None:
    title = create_title(name="phet_mul_all", flavours=["maxi"])
    application = create_application(
        title=title, flavour="maxi", store="android", name="phet", enabled=True
    )
    publication = create_publication(
        application=application,
        status="success",
    )

    response = client.post(
        f"/v1/publications/{publication.id}/cancel",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_create_publication_forbidden_without_publication_grant(
    client: TestClient,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    create_collection: Callable[..., Collection],
    create_account: Callable[..., Account],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Context, "publication_stores", ["android"])

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
    collection = create_collection(title_ids_with_paths=[(title.id, "other")])
    editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    create_collection_permission(dbsession, collection.id, editor.id)
    token = generate_access_token(issue_time=getnow(), account_id=str(editor.id))

    response = client.post(
        "/v1/publications",
        json={
            "title_identifier": str(title.id),
            "flavour": "maxi",
            "store": "android",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_create_publication_allowed_with_publication_grant(
    client: TestClient,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_application: Callable[..., Application],
    create_collection: Callable[..., Collection],
    create_account: Callable[..., Account],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Context, "publication_stores", ["android"])

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
    collection = create_collection(title_ids_with_paths=[(title.id, "other")])
    editor = create_account(permission=RoleEnum.COLLECTION_EDITOR)
    create_collection_permission(dbsession, collection.id, editor.id)
    create_publication_permission(dbsession, title.id, editor.id)
    token = generate_access_token(issue_time=getnow(), account_id=str(editor.id))

    response = client.post(
        "/v1/publications",
        json={
            "title_identifier": str(title.id),
            "flavour": "maxi",
            "store": "android",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == HTTPStatus.CREATED
