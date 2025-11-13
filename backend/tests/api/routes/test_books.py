from collections.abc import Callable
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cms_backend.db.models import Book, Title


def test_get_books_empty(client: TestClient):
    """Test get books endpoint with no books"""

    response = client.get("/v1/books")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert "meta" in response_doc
    assert response_doc["meta"]["count"] == 0
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 0
    assert "items" in response_doc
    assert response_doc["items"] == []


def test_get_books_with_data(
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test get books endpoint with books present"""

    # Create 5 books
    books: list[Book] = []
    for i in range(5):
        book = create_book(zim_metadata={"index": i, "name": f"book_{i}"})
        books.append(book)

    response = client.get("/v1/books")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 5
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 20
    assert response_doc["meta"]["page_size"] == 5
    assert len(response_doc["items"]) == 5

    # Verify the structure of returned books
    for item in response_doc["items"]:
        assert "id" in item
        assert "title_id" in item
        # Light schema should NOT include full data
        assert "article_count" not in item
        assert "media_count" not in item
        assert "size" not in item
        assert "zimcheck_result" not in item
        assert "zim_metadata" not in item
        assert "events" not in item


def test_get_books_pagination(
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test get books endpoint with pagination"""

    # Create 10 books
    for i in range(10):
        create_book(zim_metadata={"index": i})

    # Test first page
    response = client.get("/v1/books?skip=0&limit=3")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 10
    assert response_doc["meta"]["skip"] == 0
    assert response_doc["meta"]["limit"] == 3
    assert response_doc["meta"]["page_size"] == 3
    assert len(response_doc["items"]) == 3

    # Test second page
    response = client.get("/v1/books?skip=3&limit=3")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 10
    assert response_doc["meta"]["skip"] == 3
    assert response_doc["meta"]["limit"] == 3
    assert response_doc["meta"]["page_size"] == 3
    assert len(response_doc["items"]) == 3

    # Test last page (partial)
    response = client.get("/v1/books?skip=9&limit=3")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 10
    assert response_doc["meta"]["skip"] == 9
    assert response_doc["meta"]["limit"] == 3
    assert response_doc["meta"]["page_size"] == 1
    assert len(response_doc["items"]) == 1


def test_get_books_filter_by_has_title(
    client: TestClient,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
):
    """Test get books endpoint filtering by has_title"""

    title = create_title()

    # Create 3 books with title
    for _ in range(3):
        book = create_book(zim_metadata={"Name": title.name})
        title.books.append(book)

    # Create 2 books without title
    for _ in range(2):
        create_book(zim_metadata={"Name": "different_name"})

    # Filter for books with title
    response = client.get("/v1/books?has_title=true")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 3
    assert len(response_doc["items"]) == 3
    for item in response_doc["items"]:
        assert item["title_id"] is not None

    # Filter for books without title
    response = client.get("/v1/books?has_title=false")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2
    assert len(response_doc["items"]) == 2
    for item in response_doc["items"]:
        assert item["title_id"] is None


def test_get_books_combined_filters(
    client: TestClient,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
):
    """Test get books endpoint with multiple filters combined"""

    title = create_title()

    # Create various books
    # 1. With title
    book1 = create_book(zim_metadata={"Name": title.name})
    title.books.append(book1)

    # 2. Without title
    create_book(zim_metadata={"Name": "different"})

    # 3. With title
    book3 = create_book(zim_metadata={"Name": title.name})
    title.books.append(book3)

    # 4. Without title
    create_book(zim_metadata={"Name": "another"})

    # Filter for books with title
    response = client.get("/v1/books?has_title=true")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2

    # Filter for books without title
    response = client.get("/v1/books?has_title=false")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2


def test_get_books_filter_by_id(
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test get books endpoint passes id filter to database layer"""
    from uuid import UUID

    # Create books with specific UUIDs for partial matching
    book1 = create_book(
        _id=UUID("12345678-1234-5678-1234-567812345678"),
        zim_metadata={"test": "book1"},
    )
    create_book(
        _id=UUID("87654321-4321-8765-4321-876543218765"),
        zim_metadata={"test": "book2"},
    )

    # Test that id parameter is passed through and filters correctly
    response = client.get("/v1/books?id=1234-5678")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1
    assert response_doc["items"][0]["id"] == str(book1.id)


def test_get_book_by_id(
    client: TestClient,
    book: Book,
):
    """Test get book by ID endpoint"""

    response = client.get(f"/v1/books/{book.id}")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()

    # Verify all fields are present in full schema
    assert "id" in response_doc
    assert response_doc["id"] == str(book.id)
    assert "title_id" in response_doc
    assert "article_count" in response_doc
    assert response_doc["article_count"] == book.article_count
    assert "media_count" in response_doc
    assert response_doc["media_count"] == book.media_count
    assert "size" in response_doc
    assert response_doc["size"] == book.size
    assert "zimcheck_result" in response_doc
    assert response_doc["zimcheck_result"] == book.zimcheck_result
    assert "zim_metadata" in response_doc
    assert response_doc["zim_metadata"] == book.zim_metadata
    assert "events" in response_doc
    assert response_doc["events"] == book.events
    assert "producer" in response_doc
    assert isinstance(response_doc["producer"], dict)
    assert "display_name" in response_doc["producer"]
    assert response_doc["producer"]["display_name"] == book.producer_display_name
    assert "display_url" in response_doc["producer"]
    assert response_doc["producer"]["display_url"] == book.producer_display_url
    assert "unique_id" in response_doc["producer"]
    assert response_doc["producer"]["unique_id"] == book.producer_unique_id


def test_get_book_by_id_not_found(
    client: TestClient,
    book: Book,  # noqa: ARG001 - needed for conftest
):
    """Test get book by ID endpoint when book doesn't exist"""
    from uuid import uuid4

    non_existent_id = uuid4()
    response = client.get(f"/v1/books/{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    response_doc = response.json()
    assert "success" in response_doc
    assert response_doc["success"] is False
    assert "message" in response_doc


@pytest.mark.parametrize(
    "invalid_id",
    [
        pytest.param("not-a-uuid", id="invalid-format"),
        pytest.param("1234", id="too-short"),
        pytest.param("12345678-1234-5678-1234-56781234567g", id="invalid-char"),
    ],
)
def test_get_book_by_id_invalid_uuid(
    client: TestClient,
    book: Book,  # noqa: ARG001 - needed for conftest
    invalid_id: str,
):
    """Test get book by ID endpoint with invalid UUID format"""
    response = client.get(f"/v1/books/{invalid_id}")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
