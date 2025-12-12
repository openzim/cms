from collections.abc import Callable
from datetime import timedelta
from http import HTTPStatus
from uuid import uuid4
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Library, WarehousePath
from cms_backend.utils.datetime import getnow


def test_get_library_catalog_xml_not_found_by_id(
    client: TestClient,
):
    """Test that requesting a non-existent library by ID returns 404 with empty XML"""
    non_existent_library_id = uuid4()
    response = client.get(f"/v1/libraries/{non_existent_library_id}/catalog.xml")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/xml"
    # Should return valid empty XML
    root = ET.fromstring(response.text)
    assert root.tag == "library"
    assert root.get("version") == "20110515"
    assert len(list(root)) == 0


def test_get_library_catalog_xml_not_found_by_name(
    client: TestClient,
):
    """Test that requesting a non-existent library by name returns 404 with empty XML"""
    response = client.get("/v1/libraries/nonexistent_library/catalog.xml")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/xml"
    # Should return valid empty XML
    root = ET.fromstring(response.text)
    assert root.tag == "library"
    assert root.get("version") == "20110515"
    assert len(list(root)) == 0


def test_get_library_catalog_xml_empty(
    client: TestClient,
    create_library: Callable[..., Library],
):
    """Test that an empty library returns valid XML with no books"""
    library = create_library(name="empty_library")

    response = client.get(f"/v1/libraries/{library.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/xml"

    root = ET.fromstring(response.text)
    assert root.tag == "library"
    assert root.get("version") == "20110515"
    assert len(list(root)) == 0


def test_get_library_catalog_xml_by_name(
    client: TestClient,
    dbsession: OrmSession,
    create_library: Callable[..., Library],
    create_book: Callable[..., Book],
    create_warehouse_path: Callable[..., WarehousePath],
    create_book_location: Callable[..., BookLocation],
):
    """Test that library can be queried by name"""
    # Setup
    warehouse_path = create_warehouse_path()
    create_library(name="my_library", warehouse_path_ids=[warehouse_path.id])

    book = create_book(
        name="test_title",
        flavour="full",
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
    book.status = "published"
    create_book_location(book=book, warehouse_path=warehouse_path, status="current")
    dbsession.flush()

    # Test by name
    response = client.get("/v1/libraries/my_library/catalog.xml")
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/xml"

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 1
    assert books[0].get("title") == "Test Title"


def test_get_library_catalog_xml_single_book(
    client: TestClient,
    dbsession: OrmSession,
    create_library: Callable[..., Library],
    create_book: Callable[..., Book],
    create_warehouse_path: Callable[..., WarehousePath],
    create_book_location: Callable[..., BookLocation],
):
    """Test library XML with a single book"""
    # Setup
    warehouse_path = create_warehouse_path()
    library = create_library(warehouse_path_ids=[warehouse_path.id])

    book = create_book(
        name="test_title",
        flavour="full",
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
    book.status = "published"
    create_book_location(book=book, warehouse_path=warehouse_path, status="current")
    dbsession.flush()

    # Test
    response = client.get(f"/v1/libraries/{library.id}/catalog.xml")
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


def test_get_library_catalog_xml_multiple_books_different_formats(
    client: TestClient,
    dbsession: OrmSession,
    create_library: Callable[..., Library],
    create_book: Callable[..., Book],
    create_warehouse_path: Callable[..., WarehousePath],
    create_book_location: Callable[..., BookLocation],
):
    """Test that books with different flavours are included"""
    # Setup
    warehouse_path = create_warehouse_path()
    library = create_library(warehouse_path_ids=[warehouse_path.id])

    # Create books with same name but different flavours
    book_full = create_book(
        name="wiki",
        flavour="full",
        zim_metadata={
            "Name": "wiki",
            "Title": "Wikipedia Full",
            "Description": "Full version",
            "Language": "eng",
            "Creator": "Kiwix",
            "Publisher": "Kiwix",
            "Date": "2025-01-15",
        },
    )
    book_full.status = "published"

    book_nopic = create_book(
        name="wiki",
        flavour="nopic",
        zim_metadata={
            "Name": "wiki",
            "Title": "Wikipedia No Pics",
            "Description": "No pictures version",
            "Language": "eng",
            "Creator": "Kiwix",
            "Publisher": "Kiwix",
            "Date": "2025-01-10",
        },
    )
    book_nopic.status = "published"

    create_book_location(
        book=book_full, warehouse_path=warehouse_path, status="current"
    )
    create_book_location(
        book=book_nopic, warehouse_path=warehouse_path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/libraries/{library.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 2

    # Check that we have both variants (full and nopic)
    book_titles = {book.get("title") for book in books}
    assert "Wikipedia Full" in book_titles
    assert "Wikipedia No Pics" in book_titles


def test_get_library_catalog_xml_skips_unpublished_books(
    client: TestClient,
    dbsession: OrmSession,
    create_library: Callable[..., Library],
    create_book: Callable[..., Book],
    create_warehouse_path: Callable[..., WarehousePath],
    create_book_location: Callable[..., BookLocation],
):
    """Test that unpublished books are not included"""
    # Setup
    warehouse_path = create_warehouse_path()
    library = create_library(warehouse_path_ids=[warehouse_path.id])

    # Create a published book
    published_book = create_book(
        name="published",
        flavour="full",
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
    published_book.status = "published"

    # Create an unpublished book
    unpublished_book = create_book(
        name="unpublished",
        flavour="full",
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
    unpublished_book.status = "pending_processing"

    create_book_location(
        book=published_book, warehouse_path=warehouse_path, status="current"
    )
    create_book_location(
        book=unpublished_book, warehouse_path=warehouse_path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/libraries/{library.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 1
    assert books[0].get("title") == "Published Book"


def test_get_library_catalog_xml_multiple_warehouse_paths(
    client: TestClient,
    dbsession: OrmSession,
    create_library: Callable[..., Library],
    create_book: Callable[..., Book],
    create_warehouse_path: Callable[..., WarehousePath],
    create_book_location: Callable[..., BookLocation],
):
    """Test that books from all warehouse paths in the library are included"""
    # Setup
    warehouse_path_1 = create_warehouse_path()
    warehouse_path_2 = create_warehouse_path()
    library = create_library(
        warehouse_path_ids=[warehouse_path_1.id, warehouse_path_2.id]
    )

    # Create books in different warehouse paths
    book_1 = create_book(
        name="book1",
        flavour="full",
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
    book_1.status = "published"

    book_2 = create_book(
        name="book2",
        flavour="full",
        zim_metadata={
            "Name": "book2",
            "Title": "Book 2",
            "Description": "In warehouse 2",
            "Language": "eng",
            "Creator": "Author",
            "Publisher": "Publisher",
            "Date": "2025-01-01",
        },
    )
    book_2.status = "published"

    create_book_location(book=book_1, warehouse_path=warehouse_path_1, status="current")
    create_book_location(book=book_2, warehouse_path=warehouse_path_2, status="current")
    dbsession.flush()

    # Test
    response = client.get(f"/v1/libraries/{library.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 2

    titles = {book.get("title") for book in books}
    assert "Book 1" in titles
    assert "Book 2" in titles


def test_get_library_catalog_xml_latest_book_per_name_flavour(
    client: TestClient,
    dbsession: OrmSession,
    create_library: Callable[..., Library],
    create_book: Callable[..., Book],
    create_warehouse_path: Callable[..., WarehousePath],
    create_book_location: Callable[..., BookLocation],
):
    """Test that only the latest book per name+flavour combination is returned"""
    # Setup
    warehouse_path = create_warehouse_path()
    library = create_library(warehouse_path_ids=[warehouse_path.id])

    # Create older book
    older_book = create_book(
        name="wiki",
        flavour="full",
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
    older_book.status = "published"

    # Create newer book with same name+flavour
    newer_book = create_book(
        name="wiki",
        flavour="full",
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
    newer_book.status = "published"

    create_book_location(
        book=older_book, warehouse_path=warehouse_path, status="current"
    )
    create_book_location(
        book=newer_book, warehouse_path=warehouse_path, status="current"
    )
    dbsession.flush()

    # Test
    response = client.get(f"/v1/libraries/{library.id}/catalog.xml")
    assert response.status_code == HTTPStatus.OK

    root = ET.fromstring(response.text)
    books = list(root.findall("book"))
    assert len(books) == 1

    # Should be the newer book
    assert books[0].get("title") == "Wikipedia New"
    assert books[0].get("id") == str(newer_book.id)
