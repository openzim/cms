from collections.abc import Callable
from http import HTTPStatus
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cms_backend.db.models import TitleUpload
from cms_backend.schemas.models import TaskInfo, TaskInfoFlag


def test_get_title_uploads_empty(client: TestClient):
    """Test get title_uploads endpoint with no title_uploads"""
    response = client.get("/v1/title-uploads")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == 0
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 0
    assert "items" in response_doc
    assert response_doc["items"] == []


def test_get_title_uploads_with_data(
    client: TestClient,
    create_title_upload: Callable[..., TitleUpload],
    access_token: str,
):
    """Test get title_uploads endpoint with title_uploads present"""
    # Create 5 title_uploads
    for _ in range(5):
        create_title_upload()

    response = client.get(
        "/v1/title-uploads", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 5
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 5
    assert len(response_doc["items"]) == 5

    # Verify the structure of returned title_uploads
    for item in response_doc["items"]:
        assert "id" in item
        assert "status" in item
        assert "requested_by" in item
        assert "created_at" in item
        assert "s3_url" not in item
        assert "s3_key" not in item


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
def test_get_title_uploads_pagination(
    client: TestClient,
    create_title_upload: Callable[..., TitleUpload],
    access_token: str,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test get title_uploads endpoint with pagination"""
    # Create 8 title_uploads
    for _ in range(8):
        create_title_upload()

    response = client.get(
        f"/v1/title-uploads?skip={skip}&limit={limit}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 8
    assert response_doc["meta"]["skip"] == skip
    assert response_doc["meta"]["limit"] == limit
    assert response_doc["meta"]["page_size"] == expected_count
    assert len(response_doc["items"]) == expected_count


@pytest.mark.parametrize(
    "status_filter,expected_count",
    [
        pytest.param("requested", 3, id="requested-only"),
        pytest.param("canceled", 3, id="canceled-only"),
        pytest.param("completed", 2, id="completed-only"),
    ],
)
def test_get_title_uploads_filter_by_status(
    client: TestClient,
    create_title_upload: Callable[..., TitleUpload],
    access_token: str,
    status_filter: str,
    expected_count: int,
):
    """Test get title_uploads endpoint with status filter"""
    for _ in range(3):
        create_title_upload(status="requested")
    for _ in range(3):
        create_title_upload(status="canceled")
    for _ in range(2):
        create_title_upload(status="completed")

    response = client.get(
        f"/v1/title-uploads?status={status_filter}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == expected_count
    assert len(response_doc["items"]) == expected_count
    for item in response_doc["items"]:
        assert item["status"] == status_filter


def test_get_title_upload(
    client: TestClient, title_upload: TitleUpload, access_token: str
):
    """Test get title upload by ID endpoint, mocking the Zimfarm API call"""
    mock_task_info = TaskInfo(
        id="zimfarm-task-123",
        has_email=True,
        partial_zim=False,
        status="succeeded",
        flags=[
            TaskInfoFlag(
                name="download_from",
                value="s3://my-bucket/path/to/file.zim",
            ),
        ],
        progress=100,
        rank=1,
        offliner_definition_version="2.0.0",
    )

    with patch(
        "cms_backend.api.routes.title_uploads.fetch_task_from_zimfarm",
        return_value=mock_task_info,
    ) as mock_fetch_task_from_zimfarm:
        response = client.get(
            f"/v1/title-uploads/{title_upload.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == HTTPStatus.OK
    mock_fetch_task_from_zimfarm.assert_called_once()
