from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Collection, Title
from cms_backend.db.title import get_title_by_name_or_none, get_titles, update_title
from cms_backend.schemas.orms import BaseTitleCollectionSchema


def test_get_title_by_name_or_none(
    dbsession: OrmSession,
    title: Title,  # noqa: ARG001
):
    """Create a book from a zimfarm notification"""
    assert get_title_by_name_or_none(dbsession, name="foo") is None
    test_fr_title = get_title_by_name_or_none(dbsession, name="test_en_all")
    assert test_fr_title is not None
    assert test_fr_title.name == "test_en_all"


@pytest.mark.parametrize(
    "name,expected_count",
    [
        pytest.param(None, 30, id="all"),
        pytest.param("wikipedia_\\_en", 5, id="wikipedia"),
        pytest.param("wikibook_\\_en_all", 10, id="wikibook"),
        pytest.param("wikiquote%\\_all", 15, id="wikiquote"),
    ],
)
def test_get_titles_search(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    name: str | None,
    expected_count: int,
):
    """Test that get_titles works correctly with filters"""
    for i in range(5):
        title = create_title(name=f"wikipedia{i}_en_all")
        dbsession.add(title)

    for i in range(10):
        title = create_title(name=f"wikibook{i}_en_all")
        dbsession.add(title)

    for i in range(15):
        create_title(name=f"wikiquote{i}_en_all")

    limit = 8
    results = get_titles(
        dbsession,
        skip=0,
        limit=limit,
        name=name,
    )
    assert results.nb_records == expected_count
    assert len(results.records) <= limit


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
def test_get_titles_skip(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_titles works correctly with filters"""
    for i in range(6):
        create_title(name=f"wikipedia{i}_en_all")

    results = get_titles(
        dbsession,
        skip=skip,
        limit=limit,
        name="wikipedia",
    )
    assert results.nb_records == 6
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_update_title_collection_titles(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
):
    """Test updating a title's collection_titles"""
    create_collection(name="wikipedia")
    create_collection(name="gutenberg")

    title = create_title(name="wikipedia_en_test")

    update_title(
        dbsession,
        title_id=title.id,
        maturity=None,
        collection_titles=[
            BaseTitleCollectionSchema(collection_name="wikipedia", path="wikis"),
            BaseTitleCollectionSchema(collection_name="gutenberg", path="books"),
        ],
    )

    dbsession.refresh(title)
    assert len(title.collections) == 2
    collection_names = {tc.collection.name for tc in title.collections}
    assert collection_names == {"wikipedia", "gutenberg"}


def test_update_title_collection_titles_updates_prod_books(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
):
    """Test that updating collection_titles updates locations for prod books"""
    collection1 = create_collection(name="wikipedia")

    title = create_title(name="wikipedia_en_test")

    # Create a book in prod
    book = create_book(
        zim_metadata={"Name": "wikipedia_en_test", "Date": "2024-01"},
    )
    book.location_kind = "prod"
    title.books.append(book)

    # Create current location for the book
    create_book_location(
        book=book,
        warehouse_id=collection1.warehouse_id,
        path="old_path",
        filename="test.zim",
        status="current",
    )
    dbsession.flush()

    # Update collection_titles
    create_collection(name="gutenberg")

    update_title(
        dbsession,
        title_id=title.id,
        maturity=None,
        collection_titles=[
            BaseTitleCollectionSchema(collection_name="gutenberg", path="new_path"),
        ],
    )

    dbsession.refresh(book)
    assert book.needs_file_operation is True

    target_locations = [loc for loc in book.locations if loc.status == "target"]
    assert len(target_locations) == 1
    assert str(target_locations[0].path) == "new_path"
    assert target_locations[0].filename == "test.zim"
