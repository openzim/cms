from collections.abc import Callable
from datetime import timedelta
from http import HTTPStatus
from uuid import uuid4
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
)
from cms_backend.utils.datetime import getnow


def test_get_collection_catalog_xml_not_found_by_id(
    client: TestClient,
):
    """Test that requesting a non-existent collection by ID returns 404
    with empty XML"""
    non_existent_collection_id = uuid4()
    response = client.get(f"/v1/collections/{non_existent_collection_id}/catalog.xml")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/xml"
    # Should return valid empty XML
    root = ET.fromstring(response.text)
    assert root.tag == "library"
    assert root.get("version") == "20110515"
    assert len(list(root)) == 0


def test_get_collection_catalog_xml_not_found_by_name(
    client: TestClient,
):
    """Test that requesting a non-existent collection by name returns 404
    with empty XML"""
    response = client.get("/v1/collections/nonexistent_collection/catalog.xml")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/xml"
    # Should return valid empty XML
    root = ET.fromstring(response.text)
    assert root.tag == "library"
    assert root.get("version") == "20110515"
    assert len(list(root)) == 0


def test_get_collection_catalog_xml_empty(
    client: TestClient,
    create_collection: Callable[..., Collection],
):
    """Test that an empty collection returns valid XML with no books"""
    collection = create_collection(name="empty_collection")

    response = client.get(f"/v1/collections/{collection.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/xml"

    root = ET.fromstring(response.text)
    assert root.tag == "library"
    assert root.get("version") == "20110515"
    assert len(list(root)) == 0


def _add_title_to_collection(
    dbsession: OrmSession,
    collection: Collection,
    title: Title,
    path: str,
) -> None:
    """Helper to add a title to a collection"""
    from pathlib import Path

    ct = CollectionTitle(path=Path(path))
    ct.title = title
    ct.collection = collection
    dbsession.add(ct)
    dbsession.flush()


def test_get_collection_catalog_xml_by_name(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that collection can be queried by name"""
    # Setup
    warehouse = create_warehouse()
    collection = create_collection(name="my_collection", warehouse=warehouse)
    title = create_title(name="test_title")

    # Add title to collection with a path
    path = "wikipedia"
    _add_title_to_collection(dbsession, collection, title, path)

    book = create_book(
        zim_metadata={
            "Name": "test_title",
            "Title": "Test Title",
            "Description": "A test book",
            "Language": "eng",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
        },
    )
    book.title = title
    book.status = "published"
    create_book_location(
        book=book, warehouse_id=warehouse.id, path=path, status="current"
    )
    dbsession.flush()

    # Test by name
    response = client.get("/v1/collections/my_collection/catalog.xml")
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/xml"

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 1
    assert books[0].get("title") == "Test Title"


def test_get_collection_catalog_xml_single_book(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test collection XML with a single book"""
    # Setup
    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="test_title")

    path = "wikipedia"
    _add_title_to_collection(dbsession, collection, title, path)

    book = create_book(
        zim_metadata={
            "Name": "test_title",
            "Title": "Test Title",
            "Description": "A test book",
            "Language": "eng",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Tags": "_category:test;_pictures:yes",
        },
    )
    book.title = title
    book.status = "published"
    create_book_location(
        book=book, warehouse_id=warehouse.id, path=path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/collections/{collection.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/xml"

    root = ET.fromstring(response.text)
    assert root.tag == "library"
    assert root.get("version") == "20110515"

    books = list(root.findall("book"))
    assert len(books) == 1

    book_elem = books[0]
    assert book_elem.get("id") == str(book.id)
    assert book_elem.get("title") == "Test Title"
    assert book_elem.get("description") == "A test book"
    assert book_elem.get("language") == "eng"
    assert book_elem.get("creator") == "Test Creator"
    assert book_elem.get("publisher") == "Test Publisher"
    assert book_elem.get("name") == "test_title"
    assert book_elem.get("date") == "2025-01-01"
    assert book_elem.get("size") == str(book.size)
    assert book_elem.get("mediaCount") == str(book.media_count)
    assert book_elem.get("articleCount") == str(book.article_count)
    assert book_elem.get("tags") == "_category:test;_pictures:yes"


def test_get_collection_catalog_xml_multiple_books_different_formats(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that books with different flavours in same name are properly handled"""
    # Setup
    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="wiki")

    path = "wikipedia"
    _add_title_to_collection(dbsession, collection, title, path)

    # Create old book that will be superseded
    book_old = create_book(
        zim_metadata={
            "Name": "wiki",
            "Title": "Wikipedia Old",
            "Description": "Old version",
            "Language": "eng",
            "Creator": "Kiwix",
            "Publisher": "Kiwix",
            "Date": "2025-01-01",
            "Flavour": "full",
        },
    )
    book_old.title = title
    book_old.status = "published"
    dbsession.flush()
    create_book_location(
        book=book_old, warehouse_id=warehouse.id, path=path, status="current"
    )

    # Create newer book with same flavour (should supersede old)
    book_new = create_book(
        zim_metadata={
            "Name": "wiki",
            "Title": "Wikipedia New",
            "Description": "New version",
            "Language": "eng",
            "Creator": "Kiwix",
            "Publisher": "Kiwix",
            "Date": "2025-01-15",
            "Flavour": "full",
        },
    )
    book_new.title = title
    book_new.status = "published"
    dbsession.flush()
    create_book_location(
        book=book_new, warehouse_id=warehouse.id, path=path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/collections/{collection.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    # Only the newest book should be returned
    assert len(books) == 1
    assert books[0].get("title") == "Wikipedia New"


def test_get_collection_catalog_xml_skips_unpublished_books(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that unpublished books are not included"""
    # Setup
    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="test")

    path = "test"
    _add_title_to_collection(dbsession, collection, title, path)

    # Create a published book
    published_book = create_book(
        zim_metadata={
            "Name": "published",
            "Title": "Published Book",
            "Description": "Published",
            "Language": "eng",
            "Creator": "Author",
            "Publisher": "Publisher",
            "Date": "2025-01-01",
        },
    )
    published_book.title = title
    published_book.status = "published"

    # Create an unpublished book
    unpublished_book = create_book(
        zim_metadata={
            "Name": "unpublished",
            "Title": "Unpublished Book",
            "Description": "Not published",
            "Language": "eng",
            "Creator": "Author",
            "Publisher": "Publisher",
            "Date": "2025-01-01",
        },
    )
    unpublished_book.title = title
    unpublished_book.status = "pending_processing"

    create_book_location(
        book=published_book, warehouse_id=warehouse.id, path=path, status="current"
    )
    create_book_location(
        book=unpublished_book, warehouse_id=warehouse.id, path=path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/collections/{collection.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 1
    assert books[0].get("title") == "Published Book"


def test_get_collection_catalog_xml_single_warehouse(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that a collection with a single warehouse returns correct books"""
    # Each collection is tied to exactly one warehouse, so this tests that design
    warehouse = create_warehouse(name="warehouse1")
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="book1")

    path = "book1"
    _add_title_to_collection(dbsession, collection, title, path)

    book_1 = create_book(
        zim_metadata={
            "Name": "book1",
            "Title": "Book 1",
            "Description": "In warehouse 1",
            "Language": "eng",
            "Creator": "Author",
            "Publisher": "Publisher",
            "Date": "2025-01-01",
        },
    )
    book_1.title = title
    book_1.status = "published"

    create_book_location(
        book=book_1, warehouse_id=warehouse.id, path=path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/collections/{collection.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 1
    assert books[0].get("title") == "Book 1"


def test_get_collection_catalog_xml_latest_book_per_name_flavour(
    client: TestClient,
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that only the latest book per name+flavour combination is returned"""
    # Setup
    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)
    title = create_title(name="wiki")

    path = "wikipedia"
    _add_title_to_collection(dbsession, collection, title, path)

    # Create older book
    older_book = create_book(
        created_at=getnow() - timedelta(days=30),
        zim_metadata={
            "Name": "wiki",
            "Title": "Wikipedia Old",
            "Description": "Older version",
            "Language": "eng",
            "Creator": "Kiwix",
            "Publisher": "Kiwix",
            "Date": "2024-12-01",
        },
    )
    older_book.title = title
    older_book.status = "published"

    # Create newer book with same name+flavour
    newer_book = create_book(
        created_at=getnow(),
        zim_metadata={
            "Name": "wiki",
            "Title": "Wikipedia New",
            "Description": "Latest version",
            "Language": "eng",
            "Creator": "Kiwix",
            "Publisher": "Kiwix",
            "Date": "2025-01-01",
        },
    )
    newer_book.title = title
    newer_book.status = "published"

    create_book_location(
        book=older_book, warehouse_id=warehouse.id, path=path, status="current"
    )
    create_book_location(
        book=newer_book, warehouse_id=warehouse.id, path=path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/collections/{collection.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 1

    # Should be the newer book
    assert books[0].get("title") == "Wikipedia New"
    assert books[0].get("id") == str(newer_book.id)
