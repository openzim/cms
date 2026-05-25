from collections.abc import Callable

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Event,
    Title,
)
from cms_backend.db.title import (
    archive_title,
    get_title_by_name_or_none,
    get_titles,
    restore_title,
    update_title,
)
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


def test_update_title_name(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
):
    """Test updating a title's name"""
    create_collection(name="wikipedia")

    title = create_title(name="wikipedia_en_test")

    update_title(dbsession, title_id=title.id, name="wikipedia_en")

    dbsession.refresh(title)
    assert title.name == "wikipedia_en"

    events = dbsession.scalars(
        select(Event).where(Event.topic == "title_modified")
    ).all()
    assert len(events) == 1
    assert events[0].payload["action"] == "updated"
    assert events[0].payload["name"] == "wikipedia_en"
    assert events[0].payload["id"] == str(title.id)


def test_update_title_collection_titles(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_book: Callable[..., Book],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    """Test updating a title's collection_titles"""
    collection = create_collection(name="wikipedia")
    title = create_title(name="wikipedia_en_test")
    create_collection_title(title, collection, path="wikis")
    create_collection(name="gutenberg")

    # Create a book in prod
    book = create_book(
        zim_metadata={"Name": "wikipedia_en_test", "Date": "2024-01"},
    )
    book.location_kind = "prod"
    title.books.append(book)

    # Create current location for the book
    create_book_location(
        book=book,
        warehouse_id=collection.warehouse_id,
        path="old_path",
        filename="test.zim",
        status="current",
    )
    dbsession.flush()

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

    dbsession.refresh(book)
    assert book.needs_file_operation is True

    target_locations = [loc for loc in book.locations if loc.status == "target"]
    assert len(target_locations) == 2


def test_archive_title(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_book: Callable[..., Book],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    """Test marking a book as archived"""
    collection = create_collection(name="wikipedia")
    title = create_title(name="wikipedia_en_test")
    create_collection_title(title, collection, path="wikis")

    # Create a book in prod
    book = create_book(
        zim_metadata={"Name": "wikipedia_en_test", "Date": "2024-01"},
    )
    book.location_kind = "prod"
    title.books.append(book)

    # Create current location for the book
    create_book_location(
        book=book,
        warehouse_id=collection.warehouse_id,
        path="old_path",
        filename="test.zim",
        status="current",
    )
    dbsession.flush()

    title = archive_title(dbsession, str(title.id))

    assert title.archived is True
    for book in title.books:
        assert book.location_kind == "to_delete"


def test_restore_title(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_book: Callable[..., Book],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
):
    """Test restoration of archived title"""
    collection = create_collection(name="wikipedia")
    title = create_title(name="wikipedia_en_test")
    create_collection_title(title, collection, path="wikis")

    # Create a book in prod
    book = create_book(
        zim_metadata={"Name": "wikipedia_en_test", "Date": "2024-01"},
    )
    book.location_kind = "prod"
    title.books.append(book)

    # Create current location for the book
    create_book_location(
        book=book,
        warehouse_id=collection.warehouse_id,
        path="old_path",
        filename="test.zim",
        status="current",
    )
    dbsession.flush()

    archive_title(dbsession, str(title.id))
    title = restore_title(dbsession, str(title.id))

    assert title.archived is False
    for book in title.books:
        assert book.location_kind == "prod"


def test_update_title_metadata(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    """Test updating title metadata fields"""
    title = create_title(name="wikipedia_en_test")

    updated_title = update_title(
        dbsession,
        title_id=title.id,
        _title="Wikipedia in English",
        creator="Wikipedia Contributors",
        publisher="Kiwix",
        language="eng",
        description="A free encyclopedia",
        long_description="Wikipedia is a free online encyclopedia.",
        illustration_48x48_at_1="data:image/png;base64,test",
        license_="CC-BY-SA",
        relation="wikipedia",
        source="https://en.wikipedia.org",
    )

    dbsession.refresh(updated_title)
    assert updated_title.title == "Wikipedia in English"
    assert updated_title.creator == "Wikipedia Contributors"
    assert updated_title.publisher == "Kiwix"
    assert updated_title.language == "eng"
    assert updated_title.description == "A free encyclopedia"
    assert updated_title.long_description == "Wikipedia is a free online encyclopedia."
    assert updated_title.illustration_48x48_at_1 == "data:image/png;base64,test"
    assert updated_title.license == "CC-BY-SA"
    assert updated_title.relation == "wikipedia"
    assert updated_title.source == "https://en.wikipedia.org"

    assert any("title updated" in event for event in updated_title.events)
    assert any("creator updated" in event for event in updated_title.events)
    assert any("publisher updated" in event for event in updated_title.events)
    assert any("language updated" in event for event in updated_title.events)
    assert any("description updated" in event for event in updated_title.events)
    assert any("long description updated" in event for event in updated_title.events)
    assert any("license updated" in event for event in updated_title.events)
    assert any("relation updated" in event for event in updated_title.events)
    assert any("source updated" in event for event in updated_title.events)


def test_update_title_metadata_no_change(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    """Test updating title with same values doesn't create events"""
    title = create_title(name="wikipedia_en_test")

    update_title(
        dbsession,
        title_id=title.id,
        _title="Wikipedia",
        creator="Contributors",
    )
    dbsession.refresh(title)

    initial_event_count = len(title.events)

    update_title(
        dbsession,
        title_id=title.id,
        _title="Wikipedia",
        creator="Contributors",
    )
    dbsession.refresh(title)

    assert len(title.events) == initial_event_count
