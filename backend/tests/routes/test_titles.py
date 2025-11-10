from collections.abc import Callable
from http import HTTPStatus
from uuid import uuid4

from fastapi.testclient import TestClient

from cms_backend.db.models import Book, Title, WarehousePath


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


def test_get_title_by_id(
    client: TestClient,
    create_title: Callable[..., Title],
):
    """Test retrieving a title by ID returns full details"""
    title = create_title(
        name="wikipedia_en_test",
        producer_unique_id="550e8400-e29b-41d4-a716-446655440000",
        producer_display_name="farm.openzim.org: wikipedia_en_test",
        producer_display_url="https://farm.openzim.org/recipes/wikipedia_en_test",
    )

    response = client.get(f"/v1/titles/{title.id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify all TitleFullSchema fields are present
    assert set(data.keys()) == {
        "id",
        "name",
        "producer_unique_id",
        "producer_display_name",
        "producer_display_url",
        "dev_warehouse_path_id",
        "prod_warehouse_path_id",
        "in_prod",
        "events",
        "books",
    }

    # Verify field values
    assert data["id"] == str(title.id)
    assert data["name"] == "wikipedia_en_test"
    assert data["producer_unique_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["producer_display_name"] == "farm.openzim.org: wikipedia_en_test"
    assert (
        data["producer_display_url"]
        == "https://farm.openzim.org/recipes/wikipedia_en_test"
    )
    assert data["dev_warehouse_path_id"] == str(title.dev_warehouse_path_id)
    assert data["prod_warehouse_path_id"] == str(title.prod_warehouse_path_id)
    assert data["in_prod"] == title.in_prod
    assert isinstance(data["events"], list)
    assert isinstance(data["books"], list)
    assert len(data["books"]) == 0


def test_get_title_by_id_with_books(
    client: TestClient,
    dbsession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test retrieving a title with associated books"""
    title = create_title(
        name="wikipedia_en_test",
        producer_unique_id="550e8400-e29b-41d4-a716-446655440000",
    )

    # Create books associated with this title
    book1 = create_book(
        zim_metadata={"Name": "wikipedia_en_test"},
        producer_unique_id=title.producer_unique_id,
        producer_display_name="farm.openzim.org: wikipedia_en_test",
        producer_display_url="https://farm.openzim.org/recipes/wikipedia_en_test",
    )
    book2 = create_book(
        zim_metadata={"Name": "wikipedia_en_test"},
        producer_unique_id=title.producer_unique_id,
        producer_display_name="farm.openzim.org: wikipedia_en_test",
        producer_display_url="https://farm.openzim.org/recipes/wikipedia_en_test",
    )

    # Associate books with title
    title.books.append(book1)
    title.books.append(book2)
    dbsession.flush()  # Flush to update title_id on books

    response = client.get(f"/v1/titles/{title.id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify books are included
    assert len(data["books"]) == 2
    assert set(data["books"][0].keys()) == {"id", "title_id", "status"}
    assert data["books"][0]["title_id"] == str(title.id)
    assert data["books"][1]["title_id"] == str(title.id)

    # Verify book IDs match
    book_ids_in_response = {book["id"] for book in data["books"]}
    assert str(book1.id) in book_ids_in_response
    assert str(book2.id) in book_ids_in_response


def test_get_title_by_id_not_found(client: TestClient):
    """Test retrieving a non-existent title returns 404"""
    non_existent_id = uuid4()
    response = client.get(f"/v1/titles/{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "does not exist" in response.json()["message"].lower()
