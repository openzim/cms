import datetime
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db.book import (
    delete_book,
    get_book,
    get_book_or_none,
    move_book,
    recover_book,
)
from cms_backend.db.books import get_books, get_zim_urls
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
)
from cms_backend.utils.datetime import getnow


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


@pytest.mark.parametrize(
    "needs_attention,expected_count",
    [
        pytest.param(None, 5, id="no-filter"),
        pytest.param(True, 4, id="needs-attention"),
        pytest.param(False, 1, id="does-not-need-attention"),
    ],
)
def test_get_books_filter_by_needs_attention(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    needs_attention: bool | None,
    expected_count: int,
):
    """Test that get_books works correctly with needs_attention filter"""

    title = create_title()

    book_with_title = create_book(zim_metadata={"Name": title.name})
    title.books.append(book_with_title)

    book_without_title = create_book()

    book_needs_processing = create_book(zim_metadata={"Name": title.name})
    title.books.append(book_needs_processing)
    book_needs_processing.needs_processing = True

    book_has_error = create_book(zim_metadata={"Name": title.name})
    title.books.append(book_has_error)
    book_has_error.has_error = True

    book_needs_file_operation = create_book(zim_metadata={"Name": title.name})
    title.books.append(book_needs_file_operation)
    book_needs_file_operation.needs_file_operation = True

    dbsession.flush()

    results = get_books(
        dbsession,
        skip=0,
        limit=20,
        needs_attention=needs_attention,
    )

    assert results.nb_records == expected_count
    assert len(results.records) == expected_count

    if needs_attention is True:
        returned_ids = {record.id for record in results.records}
        assert returned_ids == {
            book_without_title.id,
            book_needs_processing.id,
            book_has_error.id,
            book_needs_file_operation.id,
        }
    elif needs_attention is False:
        returned_ids = {record.id for record in results.records}
        assert returned_ids == {book_with_title.id}


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
    collection = create_collection(warehouse=warehouse)
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
    collection = create_collection(warehouse=warehouse)

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


@pytest.mark.parametrize(
    "location_kind,force_delete",
    [
        pytest.param("staging", False, id="staging"),
        pytest.param("prod", True, id="prod"),
    ],
)
def test_delete_book(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    monkeypatch: pytest.MonkeyPatch,
    *,
    location_kind: str,
    force_delete: bool,
):
    """Test deleting a book"""
    warehouse = create_warehouse()
    book = create_book(name="test_en_all", date="2024-01")
    book.location_kind = location_kind
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path(""),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    now = getnow()
    monkeypatch.setattr("cms_backend.db.book.getnow", lambda: now)
    delete_book(dbsession, book_id=book.id, force_delete=force_delete)

    book = get_book(dbsession, book_id=book.id)

    assert book.location_kind == "to_delete"
    assert book.needs_file_operation is True
    assert book.deletion_date is not None
    if force_delete:
        assert book.deletion_date == now
    else:
        assert book.deletion_date > now


def test_move_book_staging_to_prod(
    dbsession: OrmSession,
    warehouse: Warehouse,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
    create_book_location: Callable[..., BookLocation],
    monkeypatch: pytest.MonkeyPatch,
):
    """Test moving a book from staging to prod"""
    title = create_title(name="test_en_all")
    collection = create_collection(warehouse=warehouse)
    create_collection_title(title=title, collection=collection, path=Path("zim"))

    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    create_book_location(
        book=book,
        warehouse_id=Context.staging_warehouse_id,
        path=Context.staging_base_path,
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    now = getnow()
    monkeypatch.setattr("cms_backend.db.book.getnow", lambda: now)
    move_book(dbsession, book_id=book.id, destination="prod")

    book = get_book(dbsession, book_id=book.id)

    assert book.location_kind == "prod"
    assert book.needs_file_operation is True

    # Check that target locations were created
    target_locations = [loc for loc in book.locations if loc.status == "target"]
    assert len(target_locations) == 1
    assert target_locations[0].warehouse_id == warehouse.id
    assert target_locations[0].path == Path("zim")
    assert target_locations[0].filename == "test_en_all_2024-01.zim"


def test_move_book_same_destination_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that moving a book to its current location raises an error"""
    warehouse = create_warehouse()
    book = create_book(name="test_en_all", date="2024-01")
    book.location_kind = "staging"
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path(""),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    with pytest.raises(
        ValueError, match="Book destination must be different from current location"
    ):
        move_book(dbsession, book_id=book.id, destination="staging")


def test_move_book_no_current_location_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that moving a book without a current location raises an error"""
    book = create_book(name="test_en_all", date="2024-01")
    book.location_kind = "staging"
    dbsession.flush()

    with pytest.raises(ValueError, match="has no current location"):
        move_book(dbsession, book_id=book.id, destination="prod")


def test_move_book_no_title_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that moving a book without an associated title raises an error"""
    warehouse = create_warehouse()
    book = create_book(name="test_en_all", date="2024-01")
    book.location_kind = "staging"
    book.title = None
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path(""),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    with pytest.raises(ValueError, match="has no associated title"):
        move_book(dbsession, book_id=book.id, destination="prod")


def test_get_zim_urls_single_view_link_for_multiple_books_with_same_title_flavour(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_warehouse: Callable[..., Warehouse],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
    create_book_location: Callable[..., BookLocation],
):
    warehouse = create_warehouse()
    title = create_title(name="test_en_all")
    collection = create_collection(warehouse=warehouse)
    create_collection_title(title=title, collection=collection, path=Path(""))
    now = getnow()

    book1 = create_book(
        zim_metadata={"Name": title.name},
        created_at=now - datetime.timedelta(days=7),
        flavour="test",
    )
    book1.title = title
    title.books.append(book1)

    create_book_location(
        book=book1,
        warehouse_id=warehouse.id,
        path=Path(""),
        filename="test_en_all.zim",
        status="current",
    )

    book2 = create_book(
        zim_metadata={"Name": title.name},
        created_at=now - datetime.timedelta(days=14),
        flavour="test",
    )
    book2.title = title
    title.books.append(book2)

    create_book_location(
        book=book2,
        warehouse_id=warehouse.id,
        path=Path(""),
        filename="test_en_all-2.zim",
        status="current",
    )

    dbsession.flush()

    result = get_zim_urls(dbsession, zim_ids=[book1.id, book2.id])

    assert book1.id in result.urls
    assert book2.id in result.urls
    assert len(result.urls[book1.id]) == 2
    assert len(result.urls[book2.id]) == 1

    book1_view_url = next((u for u in result.urls[book1.id] if u.kind == "view"), None)
    assert book1_view_url is not None

    book2_view_url = next((u for u in result.urls[book2.id] if u.kind == "view"), None)
    assert book2_view_url is None


@pytest.mark.parametrize(
    "location_kind,warehouse_id,path",
    [
        pytest.param(
            "quarantine",
            Context.quarantine_warehouse_id,
            Context.quarantine_base_path,
            id="quarantine",
        ),
        pytest.param(
            "staging",
            Context.staging_warehouse_id,
            Context.staging_base_path,
            id="staging",
        ),
        pytest.param(
            "prod",
            uuid4(),
            Path("zim"),
            id="prod",
        ),
    ],
)
def test_recover_book(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    *,
    location_kind: str,
    warehouse_id: str,
    path: Path,
):
    """Test recovering a book marked for deletion"""
    warehouse = create_warehouse(warehouse_id=warehouse_id)
    book = create_book(name="test_en_all", date="2024-01")
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=path,
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    now = getnow()
    book.location_kind = "to_delete"
    book.needs_file_operation = True
    book.deletion_date = now + datetime.timedelta(days=1)
    dbsession.flush()

    book = recover_book(dbsession, book_id=book.id)

    assert book.location_kind == location_kind
    assert book.needs_file_operation is False
    assert book.deletion_date is None
    assert f"Book restored from to_delete to {location_kind}" in book.events[-1]


def test_recover_book_with_past_deletion_date(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that recovering a book with past deletion_date raises error"""
    book = create_book(name="test_en_all", date="2024-01")
    book.location_kind = "to_delete"
    book.deletion_date = getnow()
    dbsession.flush()

    with pytest.raises(RecordDoesNotExistError):
        recover_book(dbsession, book_id=book.id)


def test_recover_book_not_marked_for_deletion(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that recovering a book not marked for deletion raises an error"""
    book = create_book(name="test_en_all", date="2024-01")
    book.location_kind = "staging"
    dbsession.flush()

    with pytest.raises(RecordDoesNotExistError):
        recover_book(dbsession, book_id=book.id)


def test_recover_book_no_current_location(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that recovering a book without current location raises an error"""
    book = create_book(name="test_en_all", date="2024-01")

    book.location_kind = "to_delete"
    book.needs_file_operation = True
    book.deletion_date = getnow() + datetime.timedelta(days=1)
    dbsession.flush()

    with pytest.raises(ValueError, match="has no current location"):
        recover_book(dbsession, book_id=book.id)
