from collections.abc import Callable
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.context import Context
from cms_backend.db.collection import update_collection
from cms_backend.db.models import Account, Collection, RequestedTask, Warehouse
from cms_backend.roles import RoleEnum
from cms_backend.schemas.models import CollectionUpdateSchema
from cms_backend.utils.datetime import getnow
from cms_backend.utils.requests import Response


@pytest.fixture(autouse=True)
def setup_s3_mocks(monkeypatch: pytest.MonkeyPatch):
    """Set up required Context values for S3 upload tests."""
    monkeypatch.setattr(
        Context,
        "zim_upload_s3_bucket_uri",
        "s3+http://minio:9000/?keyId=minio_key&secretAccessKey=minio_secret&bucketName=uploads",
    )


def _mock_query_api_response(
    status_code: int = HTTPStatus.OK,
    json_data: dict[str, Any] | None = None,
    *,
    success: bool = True,
) -> MagicMock:
    """Create a mock for query_api that returns a Response-like object."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = status_code
    mock_response.success = success
    mock_response.json = json_data if json_data is not None else {}
    return mock_response


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


def test_complete_upload_recipe_creation_bad_request(
    client: TestClient,
    collection: Collection,
    access_token: str,
):
    """Test that a bad request from zimfarm recipe creation raises BadRequestError."""
    with (
        patch(
            "cms_backend.api.routes.collection.get_kiwix_storage_client"
        ) as mock_get_s3,
        patch("cms_backend.api.routes.collection.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.collection.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.collection.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.collection.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer fake-token"}

        mock_query_api.return_value = _mock_query_api_response(
            status_code=HTTPStatus.BAD_REQUEST,
            json_data={"error": "Invalid recipe config"},
            success=False,
        )

        payload = {
            "file": {
                "upload_id": "test-upload-id",
                "key": "uploads/test-collection/test.zim",
                "parts": [{"part_number": 1, "etag": "etag1"}],
            },
            "collection_path": "/other",
        }

        response = client.post(
            f"/v1/collections/{collection.name}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


def test_complete_upload_recipe_creation_server_error(
    client: TestClient,
    collection: Collection,
    access_token: str,
):
    """Test that a server error from zimfarm recipe creation raises ServerError."""
    with (
        patch(
            "cms_backend.api.routes.collection.get_kiwix_storage_client"
        ) as mock_get_s3,
        patch("cms_backend.api.routes.collection.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.collection.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.collection.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.collection.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer fake-token"}

        mock_query_api.return_value = _mock_query_api_response(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            json_data={"error": "Internal error"},
            success=False,
        )

        payload = {
            "file": {
                "upload_id": "test-upload-id",
                "key": "uploads/test-collection/test.zim",
                "parts": [{"part_number": 1, "etag": "etag1"}],
            },
            "collection_path": "/other",
        }

        response = client.post(
            f"/v1/collections/{collection.name}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_complete_upload_missing_task_id(
    client: TestClient,
    collection: Collection,
    access_token: str,
):
    """Test that a missing task_id in the response raises ServerError."""
    with (
        patch(
            "cms_backend.api.routes.collection.get_kiwix_storage_client"
        ) as mock_get_s3,
        patch("cms_backend.api.routes.collection.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.collection.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.collection.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.collection.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer access token"}

        mock_query_api.side_effect = [
            # Recipe creation succeeds
            _mock_query_api_response(
                status_code=201,
                json_data={"name": "zimwright_abc12345", "id": str(uuid4())},
            ),
            # Task request succeeds but "requested" list is empty
            _mock_query_api_response(
                status_code=201,
                json_data={"requested": []},
            ),
        ]

        payload = {
            "file": {
                "upload_id": "test-upload-id",
                "key": "uploads/test-collection/test.zim",
                "parts": [{"part_number": 1, "etag": "etag1"}],
            },
            "collection_path": "/other",
        }

        response = client.post(
            f"/v1/collections/{collection.name}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_complete_upload_persists_requested_task(
    dbsession: OrmSession,
    client: TestClient,
    collection: Collection,
    account: Account,
    access_token: str,
):
    """Test that a RequestedTask record is created in the database."""
    task_id = uuid4()

    with (
        patch(
            "cms_backend.api.routes.collection.get_kiwix_storage_client"
        ) as mock_get_s3,
        patch("cms_backend.api.routes.collection.complete_multipart_upload"),
        patch(
            "cms_backend.api.routes.collection.generate_view_presigned_url"
        ) as mock_presigned,
        patch("cms_backend.api.routes.collection.query_api") as mock_query_api,
        patch(
            "cms_backend.api.routes.collection.zimfarm_client_token_provider.get_authorization_header"
        ) as mock_auth_header,
    ):
        mock_s3_client = MagicMock()
        mock_get_s3.return_value = mock_s3_client
        mock_presigned.return_value = "https://example.com/presigned"
        mock_auth_header.return_value = {"Authorization": "Bearer access-token"}
        mock_query_api.side_effect = [
            # POST /recipes - create recipe
            _mock_query_api_response(
                status_code=HTTPStatus.CREATED,
                json_data={"name": "zimwright_abc12345", "id": str(uuid4())},
            ),
            # POST /requested-tasks - request task
            _mock_query_api_response(
                status_code=HTTPStatus.CREATED,
                json_data={"requested": [str(task_id)]},
            ),
            # DELETE /recipes/{name} - delete recipe
            _mock_query_api_response(status_code=HTTPStatus.OK),
        ]

        payload = {
            "file": {
                "upload_id": "test-upload-id",
                "key": "uploads/test-collection/test.zim",
                "parts": [{"part_number": 1, "etag": "etag1"}],
            },
            "collection_path": "/other",
        }

        response = client.post(
            f"/v1/collections/{collection.name}/upload/complete",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == HTTPStatus.OK

        requested_task = dbsession.get(RequestedTask, task_id)
        assert requested_task is not None
        assert requested_task.s3_key == "uploads/test-collection/test.zim"
        assert requested_task.requested_by_id == account.id
        assert requested_task.collection_id == collection.id
        assert requested_task.status == "requested"
