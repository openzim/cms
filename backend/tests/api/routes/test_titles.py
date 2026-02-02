from collections.abc import Callable
from http import HTTPStatus
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, Title


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
        "maturity",
    }
    assert data["items"][0]["name"] == "wikipedia_fr_all"


def test_create_title_required_fields_only(
    client: TestClient,
    dbsession: OrmSession,
):
    """Test creating a title with only required fields"""
    title_data = {
        "name": "wikipedia_en_test",
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


def test_create_title_duplicate_name(
    client: TestClient,
):
    """Test creating a title with duplicate name returns conflict error"""
    title_data = {
        "name": "wikipedia_en_duplicate",
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
    )

    response = client.get(f"/v1/titles/{title.id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify TitleFullSchema fields
    assert set(data.keys()) == {
        "id",
        "name",
        "maturity",
        "events",
        "books",
        "collections",
    }

    # Verify field values
    assert data["id"] == str(title.id)
    assert data["name"] == "wikipedia_en_test"
    assert isinstance(data["events"], list)
    assert isinstance(data["books"], list)
    assert len(data["books"]) == 0


def test_get_title_by_id_with_books(
    client: TestClient,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test retrieving a title with associated books"""
    title = create_title(
        name="wikipedia_en_test",
    )

    # Create books associated with this title
    book1 = create_book(
        zim_metadata={"Name": "wikipedia_en_test"},
    )
    book2 = create_book(
        zim_metadata={"Name": "wikipedia_en_test"},
    )

    # Associate books with title
    title.books.append(book1)
    title.books.append(book2)
    dbsession.flush()

    response = client.get(f"/v1/titles/{title.id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    # Verify books are included
    assert len(data["books"]) == 2
    assert set(data["books"][0].keys()) == {
        "id",
        "title_id",
        "needs_processing",
        "has_error",
        "needs_file_operation",
        "location_kind",
        "created_at",
        "name",
        "date",
        "flavour",
    }
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
