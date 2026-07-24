from collections.abc import Callable
from http import HTTPStatus

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.db.collection import update_collection
from cms_backend.db.models import Account, Collection, Warehouse
from cms_backend.roles import RoleEnum
from cms_backend.schemas.models import CollectionUpdateSchema
from cms_backend.utils.datetime import getnow


def test_get_collections_empty(client: TestClient):
    """Test get collections endpoint with no collection"""

    response = client.get("/v1/collections")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == 0
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 0
    assert "items" in response_doc
    assert response_doc["items"] == []


@pytest.mark.parametrize(
    "skip,limit,is_private,nb_records,page_size",
    [
        pytest.param(0, 3, "false", 4, 3, id="first-page-public-collections"),
        pytest.param(0, 3, "true", 5, 3, id="first-page-private-collections"),
        pytest.param(0, 3, None, 9, 3, id="first-page-all-collections"),
        pytest.param(3, 3, "false", 4, 1, id="second-page-public-collections"),
        pytest.param(3, 3, "true", 5, 2, id="second-page-private-collections"),
        pytest.param(3, 3, None, 9, 3, id="second-page-all-collections"),
        pytest.param(6, 3, "false", 4, 0, id="third-page-public-collections"),
        pytest.param(6, 3, "true", 5, 0, id="third-page-private-collections"),
        pytest.param(6, 3, None, 9, 3, id="third-page-all-collections"),
    ],
)
def test_get_collections_pagination(
    client: TestClient,
    create_collection: Callable[..., Collection],
    access_token: str,
    *,
    skip: int,
    limit: int,
    is_private: bool | None,
    nb_records: int,
    page_size: int,
):
    """Test that get_collections works correctly with skip and limit"""

    # Create 9 (5 private, 4 public) collections with different settings
    for i in range(9):
        create_collection(is_private=i % 2 == 0)

    query = f"/v1/collections?skip={skip}&limit={limit}"
    if is_private is not None:
        query += f"&is_private={str(is_private).lower()}"
    response = client.get(
        query,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == nb_records
    assert response_doc["meta"]["skip"] == skip
    assert response_doc["meta"]["limit"] <= limit
    assert response_doc["meta"]["page_size"] == page_size
    assert "items" in response_doc


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.ADMIN, HTTPStatus.OK, id="admin"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_create_collection_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    warehouse: Warehouse,
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test creating a collection with different roles"""
    collection_data = {
        "name": "wikipedia_en_test",
        "warehouse_name": warehouse.name,
        "is_private": True,
    }

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.post(
        "/v1/collections",
        json=collection_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_updating_collection_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    collection: Collection,
    warehouse: Warehouse,
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test updating a collection with different roles"""
    collection_data = {
        "name": collection.name + "update",
        "warehouse_name": warehouse.name,
    }

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.patch(
        f"/v1/collections/{collection.name}",
        json=collection_data,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_get_collection(client: TestClient, collection: Collection, access_token: str):
    """Test retrieving a collection"""
    response = client.get(
        f"/v1/collections/{collection.name}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["name"] == collection.name
    assert data["warehouse"] == collection.warehouse.name
    assert data["download_base_url"] == collection.download_base_url
    assert data["view_base_url"] == collection.view_base_url


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
def test_get_collection_history(
    dbsession: OrmSession,
    client: TestClient,
    create_collection: Callable[..., Collection],
    faker: Faker,
    access_token: str,
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving collection history"""
    collection = create_collection()
    for i in range(5):
        update_collection(
            dbsession,
            collection_id=collection.name,
            author_id=account.id,
            request=CollectionUpdateSchema(
                name=faker.slug(),
                comment=f"Update {i}",
            ),
        )

    response = client.get(
        f"/v1/collections/{collection.name}/history?skip={skip}&limit={limit}",
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
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_get_collection_history_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_collection: Callable[..., Collection],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test retrieving book history with different roles"""
    collection = create_collection()

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.get(
        f"/v1/collections/{collection.name}/history?skip=0&limit=10",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_get_collection_history_entry(
    client: TestClient,
    create_collection: Callable[..., Collection],
    access_token: str,
):
    """Test retrieving a specific history entry using title name"""
    collection = create_collection()
    history_id = collection.history_entries[0].id
    response = client.get(
        f"/v1/collections/{collection.name}/history/{history_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.GLOBAL_EDITOR, HTTPStatus.OK, id="global-editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_revert_collection_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    faker: Faker,
    create_collection: Callable[..., Collection],
    create_account: Callable[..., Account],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test reverting a book with different roles"""
    collection = create_collection()
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    collection = update_collection(
        dbsession,
        collection_id=collection.name,
        author_id=account.id,
        request=CollectionUpdateSchema(
            name=faker.slug(),
            comment="Update 1",
        ),
    )
    assert len(collection.history_entries) == 2
    history_id = collection.history_entries[0].id
    response = client.patch(
        f"/v1/collections/{collection.name}/revert/{history_id}",
        json={"comment": "Reverting"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code
