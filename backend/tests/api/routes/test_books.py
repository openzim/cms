import datetime
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.token import generate_access_token
from cms_backend.context import Context
from cms_backend.db.book import update_book
from cms_backend.db.models import (
    Account,
    Book,
    BookLocation,
    Collection,
    Title,
    Warehouse,
)
from cms_backend.roles import RoleEnum
from cms_backend.schemas.models import BookUpdateSchema
from cms_backend.utils.datetime import getnow


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


@pytest.mark.parametrize(
    "needs_attention,expected_count",
    [
        pytest.param(None, 5, id="no-filter"),
        pytest.param(True, 4, id="needs-attention"),
        pytest.param(False, 1, id="does-not-need-attention"),
    ],
)
def test_get_books_filter_by_needs_attention(
    *,
    client: TestClient,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    needs_attention: bool | None,
    expected_count: int,
):
    """Test get books endpoint filtering by needs_attention"""

    title = create_title()

    book_with_title = create_book(
        zim_metadata={"Name": title.name}, location_kind="prod"
    )
    title.books.append(book_with_title)

    book_without_title = create_book(zim_metadata={"Name": "different_name"})

    book_needs_processing = create_book(zim_metadata={"Name": title.name})
    title.books.append(book_needs_processing)
    book_needs_processing.needs_processing = True

    book_has_error = create_book(zim_metadata={"Name": title.name})
    title.books.append(book_has_error)
    book_has_error.has_error = True

    book_needs_file_operation = create_book(zim_metadata={"Name": title.name})
    title.books.append(book_needs_file_operation)
    book_needs_file_operation.needs_file_operation = True

    url = (
        "/v1/books"
        if needs_attention is None
        else f"/v1/books?needs_attention={str(needs_attention).lower()}"
    )
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == expected_count
    assert len(response_doc["items"]) == expected_count

    if needs_attention is True:
        returned_ids = {item["id"] for item in response_doc["items"]}
        assert returned_ids == {
            str(book_without_title.id),
            str(book_needs_processing.id),
            str(book_has_error.id),
            str(book_needs_file_operation.id),
        }

    if needs_attention is False:
        returned_ids = {item["id"] for item in response_doc["items"]}
        assert returned_ids == {str(book_with_title.id)}


def test_get_books_filter_by_id(
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test get books endpoint passes id filter to database layer"""

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


def test_get_books_filter_by_offliner(
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test get books endpoint passes offliner filter to database layer"""

    book1 = create_book(
        _id=UUID("12345678-1234-5678-1234-567812345678"),
        zim_metadata={"test": "book1", "Scraper": "mwoffliner 1.17.5"},
    )
    create_book(
        _id=UUID("87654321-4321-8765-4321-876543218765"),
        zim_metadata={"test": "book2", "Scraper": "sotoki 1.14"},
    )

    # Test that offliner parameter is passed through and filters correctly
    response = client.get("/v1/books?offliner=mwoffliner")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1
    assert response_doc["items"][0]["id"] == str(book1.id)


def test_get_books_filter_by_issues(
    dbsession: OrmSession,
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test get books endpoint passes scraper filter to database layer"""

    book1 = create_book(
        _id=UUID("12345678-1234-5678-1234-567812345678"),
        zim_metadata={"test": "book1", "Scraper": "mwoffliner 1.17.5"},
    )
    book1.issues = ["flavour mismatch"]
    dbsession.add(book1)
    dbsession.flush()

    create_book(
        _id=UUID("87654321-4321-8765-4321-876543218765"),
        zim_metadata={"test": "book2", "Scraper": "sotoki 1.14"},
    )

    # Test that scraper parameter is passed through and filters correctly
    response = client.get("/v1/books?issue=flavour mismatch")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1
    assert response_doc["items"][0]["id"] == str(book1.id)


def test_get_book_languages(
    client: TestClient,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test books languages endpoint returns sorted distinct production languages."""
    prod_book = create_book(zim_metadata={"Language": "eng, fra"})
    prod_book.location_kind = "prod"

    other_prod_book = create_book(zim_metadata={"Language": " deu ,eng, ,spa "})
    other_prod_book.location_kind = "prod"

    create_book(zim_metadata={"Language": "hin"})
    staging_book = create_book(zim_metadata={"Language": "ita"})
    staging_book.location_kind = "staging"

    blank_language_book = create_book(zim_metadata={"Language": " , "})
    blank_language_book.location_kind = "prod"

    missing_language_book = create_book(zim_metadata={"Name": "no-language"})
    missing_language_book.location_kind = "prod"

    dbsession.flush()

    response = client.get("/v1/books/languages")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"languages": ["deu", "eng", "fra", "spa"]}


def test_get_book_flavours(
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test books flavours endpoint returns sorted distinct flavours."""
    for flavour in ["maxi", "mini", "nopic", "maxi", "mini"]:
        create_book(flavour=flavour)

    response = client.get("/v1/books/flavours")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["items"] == ["maxi", "mini", "nopic"]
    assert response_doc["meta"]["count"] == 3


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
    assert "zimcheck_result_url" in response_doc
    assert response_doc["zimcheck_result_url"] == book.zimcheck_result_url
    assert "zim_metadata" in response_doc
    assert response_doc["zim_metadata"] == book.zim_metadata
    assert "events" in response_doc
    assert response_doc["events"] == book.events
    # Note: producer fields are no longer part of the Book model


def test_get_book_by_id_not_found(
    client: TestClient,
    book: Book,  # noqa: ARG001 - needed for conftest
):
    """Test get book by ID endpoint when book doesn't exist"""

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


def test_get_books_filter_by_date_range(
    client: TestClient,
    create_book: Callable[..., Book],
):
    """Test get books endpoint filtering by updated_after/before"""

    now = getnow()
    yesterday = now - datetime.timedelta(days=1)
    two_days_ago = now - datetime.timedelta(days=2)
    three_days_ago = now - datetime.timedelta(days=3)

    # Create books at different times
    create_book(updated_at=three_days_ago)
    create_book(updated_at=two_days_ago)
    create_book(updated_at=yesterday)
    create_book(updated_at=now)

    # Filter for books received after two days ago
    response = client.get(f"/v1/books?updated_after={two_days_ago.isoformat()}")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2  # yesterday and today

    # Filter for books received before yesterday
    response = client.get(f"/v1/books?updated_before={yesterday.isoformat()}")
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 2  # three days ago and two days ago

    # Filter for books in a specific range
    response = client.get(
        f"/v1/books?updated_after={three_days_ago.isoformat()}&updated_before={yesterday.isoformat()}"
    )
    assert response.status_code == HTTPStatus.OK
    response_doc = response.json()
    assert response_doc["meta"]["count"] == 1  # only two days ago


@pytest.mark.parametrize(
    "permission,expected_status_code",
    [
        pytest.param(RoleEnum.EDITOR, HTTPStatus.OK, id="editor"),
        pytest.param(RoleEnum.VIEWER, HTTPStatus.UNAUTHORIZED, id="viewer"),
    ],
)
def test_update_book_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_book: Callable[..., Book],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test updating a book with different roles"""
    book = create_book(flavour="maxi")
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.patch(
        f"/v1/books/{book.id}",
        json={"flavour": "mini"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


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
def test_get_book_history(
    dbsession: OrmSession,
    client: TestClient,
    create_book: Callable[..., Book],
    access_token: str,
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving book history"""
    book = create_book(name="wikipedia_en_test")
    for i in range(5):
        update_book(
            dbsession,
            book_id=book.id,
            author_id=account.id,
            payload=BookUpdateSchema(
                flavour=f"mini_{i}",
                comment=f"Update {i}",
            ),
        )

    response = client.get(
        f"/v1/books/{book.id}/history?skip={skip}&limit={limit}",
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
def test_get_title_history_required_permissions(
    client: TestClient,
    create_account: Callable[..., Account],
    create_book: Callable[..., Book],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test retrieving book history with different roles"""
    book = create_book(name="wikipedia_en_test")

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    response = client.get(
        f"/v1/books/{book.id}/history?skip=0&limit=10",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code


def test_get_title_history_entry(
    client: TestClient,
    create_book: Callable[..., Book],
    access_token: str,
):
    """Test retrieving a specific history entry using title name"""
    book = create_book(name="wikipedia_en_test")
    history_id = book.history_entries[0].id
    response = client.get(
        f"/v1/books/{book.id}/history/{history_id}",
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
def test_revert_book_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    create_account: Callable[..., Account],
    create_book: Callable[..., Book],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    """Test reverting a book with different roles"""
    book = create_book(name="wikipedia_en_test")
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    book = update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(
            flavour="mini",
            comment="Update 1",
        ),
    )
    assert len(book.history_entries) == 2
    history_id = book.history_entries[0].id
    response = client.patch(
        f"/v1/books/{book.id}/revert/{history_id}",
        json={"comment": "Reverting"},
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
def test_backup_book_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    create_account: Callable[..., Account],
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test backing up a book with different roles"""

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )

    backup_warehouse = create_warehouse()
    monkeypatch.setattr(Context, "backup_warehouse_id", backup_warehouse.id)
    monkeypatch.setattr(Context, "backup_base_path", Path("/backup"))

    warehouse = create_warehouse()
    title = create_title()
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    response = client.patch(
        f"/v1/books/{book.id}/backup",
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
def test_remove_book_backup_required_permissions(
    dbsession: OrmSession,
    client: TestClient,
    create_account: Callable[..., Account],
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_collection: Callable[..., Collection],
    create_warehouse: Callable[..., Warehouse],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test backing up a book with different roles"""

    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )

    backup_warehouse = create_warehouse()
    monkeypatch.setattr(Context, "backup_warehouse_id", backup_warehouse.id)
    monkeypatch.setattr(Context, "backup_base_path", Path("/backup"))

    warehouse = create_warehouse()
    title = create_title()
    create_collection(warehouse=warehouse, title_ids_with_paths=[(title.id, "zim")])
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("backup"),
        filename="test_en_all_2024-01.zim",
        status="current",
        is_backup=True,
    )
    dbsession.flush()

    response = client.patch(
        f"/v1/books/{book.id}/backup/remove",
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
def test_get_book_issues(
    client: TestClient,
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    permission: RoleEnum,
    expected_status_code: HTTPStatus,
):
    account = create_account(permission=permission)
    access_token = generate_access_token(
        account_id=str(account.id), issue_time=getnow()
    )
    warehouse = create_warehouse()
    content = {
        "Name": "test_en_all",
        "Title": "Test Article",
        "Creator": "Test Creator",
        "Publisher": "Test Publisher",
        "Date": "2025-01-01",
        "Description": "Test description",
        "Language": "eng",
        "Illustration_48x48@1": (
            "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAOklEQVR4nO3OwQkAIAwA"
            "wfRf2u1gB4kfQeYKCHcNAAAAAAAAAAAAgL96bPf7EgAAAAAAAIC/egF5uwED0gQ8ugAAAA"
            "BJRU5ErkJggg=="
        ),
    }
    title = create_title(
        name="test_en_all",
        flavours=["maxi", "mini"],
        title=content["Title"],
        creator=content["Creator"],
        publisher=content["Publisher"],
        description=content["Description"],
        language=content["Language"],
        illustration_48x48_at_1=content["Illustration_48x48@1"],
    )
    # create a collection that tolerates only 10% increase in media and article count
    create_collection(
        warehouse=warehouse,
        title_ids_with_paths=[(title.id, "zim")],
        media_count_change_threshold=0.1,
        article_count_change_threshold=0.1,
    )

    # create the latest book with media_count of 100 and article count of 105
    latest_book = create_book(
        article_count=105,
        media_count=100,
        flavour="maxi",
        title_id=title.id,
        zim_metadata=content,
        location_kind="prod",
    )

    create_book_location(
        book=latest_book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    book = create_book(
        article_count=100,
        media_count=100,
        flavour="maxi",
        title_id=title.id,
        zim_metadata=content,
    )
    dbsession.flush()

    response = client.get(
        f"/v1/books/{book.id}/issues",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == expected_status_code
