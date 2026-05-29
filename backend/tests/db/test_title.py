from collections.abc import Callable

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import (
    Account,
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
    get_title_history,
    get_title_history_entry_or_none,
    get_titles,
    restore_title,
    revert_title,
    update_title,
)
from cms_backend.schemas.models import TitleUpdateSchema
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
    account: Account,
):
    """Test updating a title's name"""
    create_collection(name="wikipedia")

    title = create_title(name="wikipedia_en_test")

    update_title(
        dbsession,
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(name="wikipedia_en"),
    )

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
    account: Account,
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
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(
            collection_titles=[
                BaseTitleCollectionSchema(collection_name="wikipedia", path="wikis"),
                BaseTitleCollectionSchema(collection_name="gutenberg", path="books"),
            ],
        ),
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
    account: Account,
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

    title = archive_title(dbsession, str(title.id), author_id=account.id)

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
    account: Account,
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

    archive_title(dbsession, str(title.id), author_id=account.id)
    title = restore_title(dbsession, str(title.id), author_id=account.id)

    assert title.archived is False
    for book in title.books:
        assert book.location_kind == "prod"


def test_update_title_metadata(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
    illustration_48x48_at_1: str,
):
    """Test updating title metadata fields"""
    title = create_title(name="wikipedia_en_test")

    updated_title = update_title(
        dbsession,
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(
            title="Wikipedia in English",
            creator="Wikipedia Contributors",
            publisher="openZIM",
            language="eng",
            description="A free encyclopedia",
            long_description="Wikipedia is a free online encyclopedia.",
            illustration_48x48_at_1=illustration_48x48_at_1,
            license="CC-BY-SA",
            relation="wikipedia",
            source="https://en.wikipedia.org",
        ),
    )

    dbsession.refresh(updated_title)
    assert updated_title.title == "Wikipedia in English"
    assert updated_title.creator == "Wikipedia Contributors"
    assert updated_title.publisher == "openZIM"
    assert updated_title.language == "eng"
    assert updated_title.description == "A free encyclopedia"
    assert updated_title.long_description == "Wikipedia is a free online encyclopedia."
    assert updated_title.illustration_48x48_at_1 == illustration_48x48_at_1
    assert updated_title.license == "CC-BY-SA"
    assert updated_title.relation == "wikipedia"
    assert updated_title.source == "https://en.wikipedia.org"


def test_update_title_metadata_no_change(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
):
    title = create_title(name="wikipedia_en_test")

    update_title(
        dbsession,
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(
            title="Wikipedia",
            creator="Contributors",
        ),
    )
    dbsession.refresh(title)

    assert title.title == "Wikipedia"
    assert title.creator == "Contributors"


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
def test_get_title_history(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving title history with pagination"""
    title = create_title(name="wikipedia_en_test")
    for i in range(5):
        update_title(
            dbsession,
            title_identifier=str(title.id),
            author_id=account.id,
            payload=TitleUpdateSchema(
                title=f"Wikipedia Version {i}",
                comment=f"Update {i}",
            ),
        )
    results = get_title_history(
        dbsession,
        title_identifier=title.name,
        skip=skip,
        limit=limit,
    )
    assert results.nb_records == 6
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_get_title_history_entry_or_none(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
):
    """Test retrieving a specific title history entry"""
    title = create_title(name="wikipedia_en_test")

    update_title(
        dbsession,
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(
            title="Wikipedia Original",
            creator="openZIM",
            comment="Initial version",
        ),
    )

    history_result = get_title_history(
        dbsession, title_identifier=str(title.id), skip=0, limit=1
    )
    history_id = history_result.records[0].id

    history_entry = get_title_history_entry_or_none(
        dbsession, title_identifier=str(title.id), history_id=history_id
    )
    assert history_entry is not None
    assert history_entry.title == "Wikipedia Original"
    assert history_entry.creator == "openZIM"
    assert history_entry.comment == "Initial version"


def test_revert_title(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_collection_title: Callable[..., CollectionTitle],
    account: Account,
    illustration_48x48_at_1: str,
):
    """Test reverting a title to a previous state"""
    collection1 = create_collection(name="wikipedia")
    create_collection(name="gutenberg")
    title = create_title(name="wikipedia_en_test")
    create_collection_title(title, collection1, path="wikis")

    # Create a history with full metadata
    update_title(
        dbsession,
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(
            title="Wikipedia Version 1",
            creator="Contributors V1",
            publisher="openZIM V1",
            language="eng",
            description="Description V1",
            long_description="Long description V1",
            illustration_48x48_at_1=illustration_48x48_at_1,
            license="CC-BY-SA 3.0",
            relation="wikipedia_v1",
            source="https://en.wikipedia.org/v1",
            flavours=["mini", "nopic"],
            maturity="stable",
            comment="First version",
        ),
    )

    history_result = get_title_history(
        dbsession, title_identifier=str(title.id), skip=0, limit=1
    )
    first_history_id = history_result.records[0].id

    # Make a second update with different values
    update_title(
        dbsession,
        title_identifier=str(title.id),
        author_id=account.id,
        payload=TitleUpdateSchema(
            title="Wikipedia Version 2",
            creator="Contributors V2",
            publisher="openZIM V2",
            language="fra",
            description="Description V2",
            long_description="Long description V2",
            license="CC-BY-SA 4.0",
            relation="wikipedia_v2",
            source="https://en.wikipedia.org/v2",
            flavours=["maxi"],
            maturity="unstable",
            collection_titles=[
                BaseTitleCollectionSchema(collection_name="wikipedia", path="wikis"),
                BaseTitleCollectionSchema(collection_name="gutenberg", path="books"),
            ],
            comment="Second version",
        ),
    )

    dbsession.refresh(title)
    assert title.title == "Wikipedia Version 2"
    assert title.creator == "Contributors V2"
    assert title.publisher == "openZIM V2"
    assert title.language == "fra"
    assert title.description == "Description V2"
    assert title.long_description == "Long description V2"
    assert title.license == "CC-BY-SA 4.0"
    assert title.relation == "wikipedia_v2"
    assert title.source == "https://en.wikipedia.org/v2"
    assert title.flavours == ["maxi"]
    assert title.maturity == "unstable"
    assert len(title.collections) == 2

    # Revert to the first version
    reverted_title = revert_title(
        dbsession,
        title_identifier=str(title.id),
        history_id=first_history_id,
        author_id=account.id,
        comment="Reverting to version 1",
    )

    # Verify all fields were reverted
    assert reverted_title.title == "Wikipedia Version 1"
    assert reverted_title.creator == "Contributors V1"
    assert reverted_title.publisher == "openZIM V1"
    assert reverted_title.language == "eng"
    assert reverted_title.description == "Description V1"
    assert reverted_title.long_description == "Long description V1"
    assert reverted_title.illustration_48x48_at_1 == illustration_48x48_at_1
    assert reverted_title.license == "CC-BY-SA 3.0"
    assert reverted_title.relation == "wikipedia_v1"
    assert reverted_title.source == "https://en.wikipedia.org/v1"
    assert reverted_title.flavours == ["mini", "nopic"]
    assert reverted_title.maturity == "stable"
    assert len(reverted_title.collections) == 1
