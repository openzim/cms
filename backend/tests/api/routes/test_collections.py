from collections.abc import Callable
from http import HTTPStatus

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.db.collection import update_collection
from cms_backend.db.models import Account, Collection, Title, Warehouse
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
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 3, 2, id="third-page-partial"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 8, id="first-page-with-high-limit"),
    ],
)
def test_get_collections_pagination(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_collections works correctly with skip and limit"""

    title1 = create_title(name="wikipedia_en_all")
    title2 = create_title(name="ted_en_all")
    title3 = create_title(name="gutenberg_en_all")

    # Create 8 collections with varying numbers of titles/paths
    for i in range(8):
        if i % 3 == 0:
            # Every third collection has multiple titles
            create_collection(
                title_ids_with_paths=[
                    (title1.id, f"/path/to/collection{i}/wikipedia"),
                    (title2.id, f"/path/to/collection{i}/ted"),
                ]
            )
        elif i % 3 == 1:
            # Some collections have a single title
            create_collection(
                title_ids_with_paths=[
                    (title3.id, f"/path/to/collection{i}/gutenberg"),
                ]
            )
        else:
            # Some collections have no titles
            create_collection()

    dbsession.flush()

    response = client.get(f"/v1/collections?skip={skip}&limit={limit}")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == 8
    assert response_doc["meta"]["skip"] == skip
    assert response_doc["meta"]["limit"] <= limit
    assert response_doc["meta"]["page_size"] == expected_count
    assert "items" in response_doc


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
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
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
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


def test_get_collection(
    client: TestClient,
    collection: Collection,
):
    """Test retrieving a collection"""
    response = client.get(f"/v1/collections/{collection.name}")
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
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
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
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
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
