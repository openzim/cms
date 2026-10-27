from collections.abc import Callable
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.db import application as db_application
from cms_backend.db.models import Account, Application, Title
from cms_backend.roles import RoleEnum
from cms_backend.schemas.models import ApplicationUpdateSchema
from cms_backend.utils.datetime import getnow


def test_get_application(
    client: TestClient,
    application: Application,
    access_token: str,
) -> None:
    response = client.get(
        f"/v1/applications/{application.name}/{application.store}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["title_id"] == str(application.title_id)
    assert data["flavour"] == application.flavour
    assert data["store"] == application.store
    assert data["name"] == application.name


def test_create_application(
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
) -> None:
    title = create_title(name="phet_mul_all", flavours=["maxi"])

    response = client.post(
        "/v1/applications",
        json={
            "title_id": str(title.id),
            "flavour": "maxi",
            "store": "android",
            "enabled": True,
            "name": "phet",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["title_id"] == str(title.id)
    assert data["title_name"] == "phet_mul_all"
    assert data["flavour"] == "maxi"
    assert data["store"] == "android"
    assert data["enabled"] is True
    assert data["name"] == "phet"


def test_create_application_rejects_duplicate(
    client: TestClient,
    create_title: Callable[..., Title],
    access_token: str,
) -> None:
    title = create_title(flavours=["maxi"])
    payload = {
        "title_id": str(title.id),
        "flavour": "maxi",
        "store": "android",
        "enabled": True,
        "name": "phet",
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.post("/v1/applications", json=payload, headers=headers)
    assert response.status_code == HTTPStatus.CREATED

    response = client.post("/v1/applications", json=payload, headers=headers)
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.parametrize(
    ("name", "store", "expected_count"),
    [
        pytest.param(None, None, 3, id="no-filters"),
        pytest.param(None, "android", 2, id="store"),
        pytest.param(None, "apple", 1, id="store-single"),
        pytest.param("phet", None, 1, id="name"),
        pytest.param("wikipedia", None, 1, id="name-other"),
        pytest.param("phet", "android", 1, id="name-and-store"),
        pytest.param("wikipedia", "android", 0, id="no-match"),
    ],
)
def test_list_applications_filters(
    client: TestClient,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    access_token: str,
    name: str | None,
    store: str | None,
    expected_count: int,
) -> None:
    phet_title = create_title(name="phet_mul_all", flavours=["maxi", "mini"])
    wikipedia_title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    create_application(title=phet_title, flavour="maxi", store="android", name="phet")
    create_application(title=phet_title, flavour="mini", store="android", name="phet2")
    create_application(
        title=wikipedia_title, flavour="maxi", store="apple", name="wikipedia"
    )

    params: dict[str, str] = {}
    if name is not None:
        params["name"] = name
    if store is not None:
        params["store"] = store

    response = client.get(
        "/v1/applications",
        params=params,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["meta"]["count"] == expected_count
    assert len(data["items"]) == expected_count


def test_update_application(
    client: TestClient,
    application: Application,
    access_token: str,
) -> None:
    response = client.patch(
        f"/v1/applications/{application.name}/{application.store}",
        json={"enabled": False, "name": "updated_app"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["enabled"] is False
    assert data["name"] == "updated_app"

    response = client.get(
        f"/v1/applications/updated_app/{application.store}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "updated_app"


def test_delete_application(
    client: TestClient,
    application: Application,
    access_token: str,
) -> None:
    response = client.delete(
        f"/v1/applications/{application.name}/{application.store}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get(
        f"/v1/applications/{application.name}/{application.store}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    "skip, limit, expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 2, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 10, 6, id="first-page-with-high-limit"),
    ],
)
def test_get_application_history(
    dbsession: OrmSession,
    client: TestClient,
    create_application: Callable[..., Application],
    account: Account,
    access_token: str,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving application history"""
    application = create_application(name="phet", store="android", enabled=True)
    name = application.name
    store = application.store

    for i in range(5):
        db_application.update_application(
            dbsession,
            name=name,
            store=store,
            author_id=account.id,
            payload=ApplicationUpdateSchema(enabled=i % 2 == 0, comment=f"Update {i}"),
        )

    response = client.get(
        f"/v1/applications/{name}/{store}/history?skip={skip}&limit={limit}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["meta"]["skip"] == skip
    assert data["meta"]["limit"] == limit
    assert data["meta"]["page_size"] == expected_count
    assert len(data["items"]) == expected_count


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.ADMIN, HTTPStatus.OK, id="admin"),
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(
            RoleEnum.GLOBAL_VIEWER, HTTPStatus.UNAUTHORIZED, id="global-viewer"
        ),
        pytest.param(
            RoleEnum.PUBLIC_VIEWER, HTTPStatus.UNAUTHORIZED, id="public-viewer"
        ),
    ],
)
def test_get_application_history_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_application: Callable[..., Application],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test retrieving application history with different roles"""
    application = create_application(name="phet", store="android")

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.get(
        f"/v1/applications/{application.name}/{application.store}/history",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_get_application_history_entry(
    client: TestClient,
    create_application: Callable[..., Application],
    access_token: str,
) -> None:
    """Test retrieving a specific application history entry"""
    application = create_application(name="phet", store="android")
    history_response = client.get(
        f"/v1/applications/{application.name}/{application.store}/history",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    history_id = history_response.json()["items"][0]["id"]

    response = client.get(
        f"/v1/applications/{application.name}/{application.store}/history/{history_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["id"] == history_id
    assert data["name"] == "phet"
    assert data["store"] == "android"


def test_get_application_history_entry_not_found(
    client: TestClient,
    application: Application,
    access_token: str,
) -> None:
    response = client.get(
        f"/v1/applications/{application.name}/{application.store}/history/{uuid4()}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_revert_application(
    dbsession: OrmSession,
    client: TestClient,
    create_application: Callable[..., Application],
    account: Account,
    access_token: str,
) -> None:
    """Test reverting an application to a previous history entry"""
    application = create_application(name="phet", store="android", enabled=True)
    store = application.store

    db_application.update_application(
        dbsession,
        name="phet",
        store=store,
        author_id=account.id,
        payload=ApplicationUpdateSchema(
            name="phet2", enabled=False, comment="Rename app"
        ),
    )

    history_response = client.get(
        f"/v1/applications/phet2/{store}/history",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    initial_entry = next(
        item
        for item in history_response.json()["items"]
        if item["comment"] == "Initial history entry"
    )

    response = client.patch(
        f"/v1/applications/phet2/{store}/revert/{initial_entry['id']}",
        json={"comment": "Reverting"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["name"] == "phet"
    assert data["enabled"] is True


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.ADMIN, HTTPStatus.OK, id="admin"),
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(
            RoleEnum.GLOBAL_VIEWER, HTTPStatus.UNAUTHORIZED, id="global-viewer"
        ),
        pytest.param(
            RoleEnum.PUBLIC_VIEWER, HTTPStatus.UNAUTHORIZED, id="public-viewer"
        ),
    ],
)
def test_revert_application_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    create_account: Callable[..., Account],
    create_application: Callable[..., Application],
    account: Account,
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test reverting an application with different roles"""
    application = create_application(name="phet", store="android", enabled=True)
    db_application.update_application(
        dbsession,
        name=application.name,
        store=application.store,
        author_id=account.id,
        payload=ApplicationUpdateSchema(enabled=False, comment="Update 1"),
    )
    history = db_application.get_application_history(
        dbsession,
        name=application.name,
        store=application.store,
        skip=0,
        limit=10,
    )
    history_id = history.records[0].id

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.patch(
        f"/v1/applications/{application.name}/{application.store}/revert/{history_id}",
        json={"comment": "Reverting"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code
