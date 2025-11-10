from collections.abc import Callable
from http import HTTPStatus

from fastapi.testclient import TestClient

from cms_backend.db.models import Title, WarehousePath


def test_get_titles_empty(client: TestClient):
    """Test that get_titles returns empty list when no titles exist"""
    response = client.get("/v1/titles?skip=0&limit=10")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "meta" in data
    assert "items" in data
    assert data["meta"]["skip"] == 0
    assert data["meta"]["limit"] == 10
    assert data["meta"]["page_size"] == 0
    assert data["meta"]["count"] == 0
    assert data["items"] == []


def test_get_titles(
    client: TestClient,
    create_title: Callable[..., Title],
):
    """Test that get_titles returns titles"""
    create_title(name="wikipedia_en_all")
    create_title(name="wikipedia_fr_all")

    response = client.get("/v1/titles?skip=1&limit=12")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["meta"]["skip"] == 1
    assert data["meta"]["limit"] == 12
    assert data["meta"]["page_size"] == 1
    assert data["meta"]["count"] == 2
    assert len(data["items"]) == 1
    assert set(data["items"][0].keys()) == {
        "id",
        "name",
        "producer_unique_id",
        "producer_display_name",
        "producer_display_url",
    }
    assert data["items"][0]["name"] == "wikipedia_fr_all"


def test_create_title_required_fields_only(
    client: TestClient,
    dbsession,
    create_warehouse_path: Callable[..., WarehousePath],
):
    """Test creating a title with only required fields"""
    dev_warehouse_path = create_warehouse_path()
    prod_warehouse_path = create_warehouse_path()

    title_data = {
        "name": "wikipedia_en_test",
        "producer_unique_id": "550e8400-e29b-41d4-a716-446655440000",
        "dev_warehouse_path_id": str(dev_warehouse_path.id),
        "prod_warehouse_path_id": str(prod_warehouse_path.id),
    }

    response = client.post("/v1/titles", json=title_data)
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert "id" in data
    assert "name" in data
    assert data["name"] == "wikipedia_en_test"

    # Verify the title was created in the database
    title = dbsession.get(Title, data["id"])
    assert title is not None
    assert title.name == "wikipedia_en_test"
    assert title.producer_unique_id == "550e8400-e29b-41d4-a716-446655440000"
    assert title.producer_display_name is None
    assert title.producer_display_url is None
    assert title.dev_warehouse_path_id == dev_warehouse_path.id
    assert title.prod_warehouse_path_id == prod_warehouse_path.id
    assert title.in_prod is False


def test_create_title_with_optional_fields(
    client: TestClient,
    dbsession,
    create_warehouse_path: Callable[..., WarehousePath],
):
    """Test creating a title with all fields including optional ones"""
    dev_warehouse_path = create_warehouse_path()
    prod_warehouse_path = create_warehouse_path()

    title_data = {
        "name": "wikipedia_fr_test",
        "producer_unique_id": "550e8400-e29b-41d4-a716-446655440001",
        "producer_display_name": "farm.openzim.org: wikipedia_fr_test",
        "producer_display_url": "https://farm.openzim.org/recipes/wikipedia_fr_test",
        "dev_warehouse_path_id": str(dev_warehouse_path.id),
        "prod_warehouse_path_id": str(prod_warehouse_path.id),
        "in_prod": True,
    }

    response = client.post("/v1/titles", json=title_data)
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert "id" in data
    assert "name" in data
    assert data["name"] == "wikipedia_fr_test"

    # Verify all fields were stored correctly
    title = dbsession.get(Title, data["id"])
    assert title is not None
    assert title.name == "wikipedia_fr_test"
    assert title.producer_unique_id == "550e8400-e29b-41d4-a716-446655440001"
    assert title.producer_display_name == "farm.openzim.org: wikipedia_fr_test"
    assert (
        title.producer_display_url
        == "https://farm.openzim.org/recipes/wikipedia_fr_test"
    )
    assert title.dev_warehouse_path_id == dev_warehouse_path.id
    assert title.prod_warehouse_path_id == prod_warehouse_path.id
    assert title.in_prod is True


def test_create_title_missing_required_field(
    client: TestClient,
    create_warehouse_path: Callable[..., WarehousePath],
):
    """Test creating a title with missing required field returns validation error"""
    dev_warehouse_path = create_warehouse_path()

    title_data = {
        "name": "wikipedia_en_incomplete",
        "producer_unique_id": "550e8400-e29b-41d4-a716-446655440002",
        "dev_warehouse_path_id": str(dev_warehouse_path.id),
        # Missing prod_warehouse_path_id
    }

    response = client.post("/v1/titles", json=title_data)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_create_title_duplicate_name(
    client: TestClient,
    create_warehouse_path: Callable[..., WarehousePath],
):
    """Test creating a title with duplicate name returns conflict error"""
    dev_warehouse_path = create_warehouse_path()
    prod_warehouse_path = create_warehouse_path()

    title_data = {
        "name": "wikipedia_en_duplicate",
        "producer_unique_id": "550e8400-e29b-41d4-a716-446655440003",
        "dev_warehouse_path_id": str(dev_warehouse_path.id),
        "prod_warehouse_path_id": str(prod_warehouse_path.id),
    }

    # Create the first title
    response = client.post("/v1/titles", json=title_data)
    assert response.status_code == HTTPStatus.OK

    # Try to create another title with the same name
    response = client.post("/v1/titles", json=title_data)
    assert response.status_code == HTTPStatus.CONFLICT
    assert "already exists" in response.json()["message"].lower()
