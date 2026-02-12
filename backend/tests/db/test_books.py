from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.books import get_book, get_book_or_none, get_books, get_zim_urls
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
)


def test_get_book_or_none_not_found(
    dbsession: OrmSession,
    book: Book,  # noqa: ARG001 - needed for conftest
):
    """Returns None if the book does not exist"""
    result = get_book_or_none(dbsession, book_id=uuid4())
    assert result is None


def test_get_book_not_found(
    dbsession: OrmSession,
    book: Book,  # noqa: ARG001 - needed for conftest
):
    """Raises an exception if the book does not exist"""
    with pytest.raises(RecordDoesNotExistError):
        get_book(dbsession, book_id=uuid4())


def test_get_book_exist(dbsession: OrmSession, book: Book):
    """Returns the book if it exists"""
    result = get_book(dbsession, book_id=book.id)
    assert result is not None
    assert result == book


def test_get_books_empty(dbsession: OrmSession):
    """Returns empty list when no books exist"""
    results = get_books(dbsession, skip=0, limit=20)
    assert results.nb_records == 0
    assert len(results.records) == 0


def test_get_books_with_data(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Returns all books"""
    # Create 5 books
    books: list[Book] = []
    for _ in range(5):
        book = create_book()
        books.append(book)

    results = get_books(dbsession, skip=0, limit=20)
    assert results.nb_records == 5
    assert len(results.records) == 5


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
def test_get_books_pagination(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_books works correctly with skip and limit"""

    # Create 8 books
    for _ in range(8):
        create_book()

    dbsession.flush()

    results = get_books(
        dbsession,
        skip=skip,
        limit=limit,
    )
    assert results.nb_records == 8
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


@pytest.mark.parametrize(
    "has_title,expected_count",
    [
        pytest.param(None, 5, id="no-filter"),
        pytest.param(True, 2, id="has-title"),
        pytest.param(False, 3, id="no-title"),
    ],
)
def test_get_books_filter_by_has_title(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    has_title: bool | None,
    expected_count: int,
):
    """Test that get_books works correctly with has_title filter"""

    title = create_title()

    # Create 2 books with title
    for _ in range(2):
        book = create_book(zim_metadata={"Name": title.name})
        title.books.append(book)

    # Create 3 books without title
    for _ in range(3):
        create_book()

    dbsession.flush()

    results = get_books(
        dbsession,
        skip=0,
        limit=20,
        has_title=has_title,
    )
    assert results.nb_records == expected_count
    assert len(results.records) == expected_count


@pytest.mark.parametrize(
    "book_id_filter,expected_count,expected_ids",
    [
        pytest.param("1234-5678-1234", 1, ["book1"], id="partial-match-book1"),
        pytest.param("8765-4321", 1, ["book2"], id="partial-match-book2"),
        pytest.param("2222-3333", 1, ["book3"], id="partial-match-book3"),
        pytest.param("1234", 1, ["book1"], id="match-1234-only-book1"),
        pytest.param("abcd", 1, ["book4"], id="lowercase-match"),
        pytest.param("ABCD", 1, ["book4"], id="uppercase-match"),
        pytest.param("AbCd", 1, ["book4"], id="mixed-case-match"),
        pytest.param("nonexistent", 0, [], id="no-match"),
        pytest.param("aaaa", 2, ["book5", "book6"], id="multiple-matches"),
        pytest.param("1111", 2, ["book3", "book5"], id="multiple-matches-with-1111"),
    ],
)
def test_get_books_book_id_filter(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    book_id_filter: str,
    expected_count: int,
    expected_ids: list[str],
):
    """Test that get_books works with book_id filter"""
    from uuid import UUID

    # Create books with specific UUIDs
    book_mapping = {
        "book1": create_book(
            _id=UUID("12345678-1234-5678-1234-567812345678"),
        ),
        "book2": create_book(
            _id=UUID("87654321-4321-8765-4321-876543218765"),
        ),
        "book3": create_book(
            _id=UUID("11111111-2222-3333-4444-555555555555"),
        ),
        "book4": create_book(
            _id=UUID("abcdefab-cdef-abcd-efab-cdefabcdefab"),
        ),
        "book5": create_book(
            _id=UUID("aaaaaaaa-1111-1111-1111-111111111111"),
        ),
        "book6": create_book(
            _id=UUID("aaaaaaaa-2222-2222-2222-222222222222"),
        ),
    }

    dbsession.flush()

    results = get_books(
        dbsession,
        skip=0,
        limit=20,
        book_id=book_id_filter,
    )

    assert results.nb_records == expected_count
    assert len(results.records) == expected_count

    # Verify the correct books were returned
    returned_ids = {str(record.id) for record in results.records}
    expected_uuid_ids = {str(book_mapping[key].id) for key in expected_ids}
    assert returned_ids == expected_uuid_ids


def test_get_books_book_id_combined_with_other_filters(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
):
    """Test book_id filter combined with other filters"""
    from uuid import UUID

    title = create_title()

    # Create books with specific characteristics
    book1 = create_book(
        _id=UUID("aaaaaaaa-1111-1111-1111-111111111111"),
        zim_metadata={"Name": title.name},
    )
    title.books.append(book1)

    book2 = create_book(
        _id=UUID("aaaaaaaa-2222-2222-2222-222222222222"),
    )

    book3 = create_book(
        _id=UUID("bbbbbbbb-3333-3333-3333-333333333333"),
        zim_metadata={"Name": title.name},
    )
    title.books.append(book3)

    dbsession.flush()

    # Filter by ID pattern "aaaa" - should match book1 and book2
    results = get_books(dbsession, skip=0, limit=20, book_id="aaaa")
    assert results.nb_records == 2

    # Filter by ID pattern "aaaa" AND has_title=true - should only match book1
    results = get_books(dbsession, skip=0, limit=20, book_id="aaaa", has_title=True)
    assert results.nb_records == 1
    assert results.records[0].id == book1.id

    # Filter by ID pattern "aaaa" AND has_title=false - should only match book2
    results = get_books(dbsession, skip=0, limit=20, book_id="aaaa", has_title=False)
    assert results.nb_records == 1
    assert results.records[0].id == book2.id

    # Filter by ID pattern "bbbb" AND has_title=true - should only match book3
    results = get_books(dbsession, skip=0, limit=20, book_id="bbbb", has_title=True)
    assert results.nb_records == 1
    assert results.records[0].id == book3.id


def test_get_zim_urls(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_warehouse: Callable[..., Warehouse],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
    create_book_location: Callable[..., BookLocation],
):
    """Test get_zim_urls returns the download and view urls for zims"""
    warehouse = create_warehouse()
    title = create_title(name="test_en_all")
    collection = create_collection(
        warehouse=warehouse,
        download_base_url="https://download.kiwix.org",
        view_base_url="https://browse.library.kiwix.org",
    )
    create_collection_title(title=title, collection=collection, path=Path(""))

    book = create_book(zim_metadata={"Name": title.name})
    book.title = title
    title.books.append(book)

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path(""),
        filename="test_en_all.zim",
        status="current",
    )

    dbsession.flush()

    result = get_zim_urls(dbsession, zim_ids=[book.id])

    assert book.id in result.urls
    assert len(result.urls[book.id]) == 2

    download_url = next((u for u in result.urls[book.id] if u.kind == "download"), None)
    assert download_url is not None
    assert str(download_url.url) == "https://download.kiwix.org/zim/test_en_all.zim"
    assert download_url.collection == collection.name

    view_url = next((u for u in result.urls[book.id] if u.kind == "view"), None)
    assert view_url is not None
    assert str(view_url.url) == "https://browse.library.kiwix.org/viewer#test_en_all"
    assert view_url.collection == collection.name


def test_get_zim_urls_book_with_subpath(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_warehouse: Callable[..., Warehouse],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
    create_book_location: Callable[..., BookLocation],
):
    """Download URL includes subpath when book is not at root"""
    from pathlib import Path

    warehouse = create_warehouse()
    title = create_title(name="test_en_all")
    collection = create_collection(
        warehouse=warehouse,
        download_base_url="https://download.kiwix.org",
        view_base_url="https://browse.library.kiwix.org",
    )

    subpath = Path("wikipedia")
    create_collection_title(title=title, collection=collection, path=subpath)

    book = create_book(zim_metadata={"Name": title.name})
    book.title = title
    title.books.append(book)

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=subpath,
        filename="test_en_all.zim",
        status="current",
    )

    dbsession.flush()

    result = get_zim_urls(dbsession, zim_ids=[book.id])
    assert book.id in result.urls
    assert len(result.urls[book.id]) == 2

    download_url = next((u for u in result.urls[book.id] if u.kind == "download"), None)
    assert download_url is not None
    assert (
        str(download_url.url)
        == "https://download.kiwix.org/zim/wikipedia/test_en_all.zim"
    )
    assert download_url.collection == collection.name

    view_url = next((u for u in result.urls[book.id] if u.kind == "view"), None)
    assert view_url is not None
    assert str(view_url.url) == "https://browse.library.kiwix.org/viewer#test_en_all"
    assert view_url.collection == collection.name
