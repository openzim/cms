from collections.abc import Callable

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.book import create_book as db_create_book
from cms_backend.db.book import (
    get_book_history,
    get_book_history_entry_or_none,
    get_differing_metadata_keys,
    revert_book,
    update_book,
)
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account, Book, Title, ZimfarmNotification
from cms_backend.db.rules import has_flavour_mismatch
from cms_backend.schemas.models import BookUpdateSchema


def test_create_book(
    dbsession: OrmSession,
    zimfarm_notification: ZimfarmNotification,
    faker: Faker,
    account: Account,
):
    """Create a book from a zimfarm notification"""
    book_id = zimfarm_notification.id  # Use zimfarm notification ID as book ID
    book = db_create_book(
        dbsession,
        author_id=account.id,
        book_id=book_id,
        article_count=faker.random_int(),
        media_count=faker.random_int(),
        size=faker.random_int(),
        zim_metadata={"key": "value"},
        zimcheck_result_url="https://www.example.com/zimcheck.json",
        zimfarm_notification=zimfarm_notification,
    )
    dbsession.flush()
    assert book.zimfarm_notification == zimfarm_notification
    assert zimfarm_notification.book_id == book.id
    assert zimfarm_notification.book == book
    assert any(
        event
        for event in zimfarm_notification.events
        if "notification transformed into book" in event
    )
    assert any(
        event for event in book.events if "created from Zimfarm notification" in event
    )


def test_get_differing_metadata_keys(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    illustration_48x48_at_1: str,
):
    """Get the different metadata keys between book and it's title."""
    title = create_title(
        title="Title",
        creator="Title Creator",
        publisher="openZIM",
        description="Title Description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )

    book = create_book(
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        }
    )
    book.title_id = title.id
    dbsession.add(book)
    dbsession.flush()

    differences = get_differing_metadata_keys(book)
    assert set(differences) == {"Title", "Creator", "Publisher", "Description"}


def test_update_deleted_book(
    dbsession: OrmSession, account: Account, create_book: Callable[..., Book]
):
    book = create_book(location_kind="deleted")
    with pytest.raises(RecordDoesNotExistError, match=r"Book .* is already deleted"):
        update_book(
            dbsession,
            book_id=book.id,
            author_id=account.id,
            payload=BookUpdateSchema(flavour="maxi"),
        )


def test_update_book_belonging_to_archived_title(
    dbsession: OrmSession,
    account: Account,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    book = create_book()
    title = create_title(archived=True)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"Book title .* is currently archived"):
        update_book(
            dbsession,
            author_id=account.id,
            book_id=book.id,
            payload=BookUpdateSchema(flavour="maxi"),
        )


def test_update_book_with_same_flavour(
    dbsession: OrmSession,
    account: Account,
    create_book: Callable[..., Book],
):
    book = create_book(flavour="maxi")
    assert book.flavour is not None
    assert len(book.history_entries) == 1
    update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(flavour=book.flavour),
    )
    assert len(book.history_entries) == 1


def test_update_book_with_different_flavour(
    dbsession: OrmSession,
    account: Account,
    create_book: Callable[..., Book],
):
    book = create_book(flavour="maxi")
    assert book.flavour is not None
    assert len(book.history_entries) == 1
    book = update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(flavour="mini"),
    )
    assert book.flavour == "mini"
    assert len(book.history_entries) == 2


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
    create_book: Callable[..., Book],
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving book history with pagination"""
    book = create_book(name="test_book", flavour="maxi")
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
    results = get_book_history(
        dbsession,
        book_id=book.id,
        skip=skip,
        limit=limit,
    )
    assert results.nb_records == 6
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_get_book_history_entry_or_none(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    account: Account,
):
    """Test retrieving a specific book history entry"""
    book = create_book(name="test_book", flavour="maxi")

    update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(
            flavour="mini",
            comment="Initial version",
        ),
    )

    history_result = get_book_history(dbsession, book_id=book.id, skip=0, limit=1)
    history_id = history_result.records[0].id

    history_entry = get_book_history_entry_or_none(
        dbsession, book_id=book.id, history_id=history_id
    )
    assert history_entry is not None
    assert history_entry.flavour == "mini"
    assert history_entry.comment == "Initial version"


def test_revert_book(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    account: Account,
):
    """Test reverting a book to a previous state"""
    book = create_book(name="test_book", flavour="maxi")

    # Create a first history entry
    update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(
            flavour="mini",
            comment="First version",
        ),
    )

    history_result = get_book_history(dbsession, book_id=book.id, skip=0, limit=1)
    first_history_id = history_result.records[0].id

    # Make a second update with different flavour
    book = update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(
            flavour="nopic",
            comment="Second version",
        ),
    )

    assert book.flavour == "nopic"

    # Revert to the first version
    reverted_book = revert_book(
        dbsession,
        book_id=book.id,
        history_id=first_history_id,
        author_id=account.id,
        comment="Reverting to version 1",
    )
    assert reverted_book.flavour == "mini"


def test_update_book_flavour_mismatch_issues(
    dbsession: OrmSession,
    account: Account,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """
    Test that book with  a flavour mismatch between it and it's title has
    it's issues reset when it's flavour is updated to the same as the title
    """
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
    book = create_book(zim_metadata=content)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    book = update_book(
        dbsession,
        author_id=account.id,
        book_id=book.id,
        payload=BookUpdateSchema(flavour="nopic"),
    )
    assert len(book.issues) == 1
    assert book.issues == ["flavour mismatch"]

    book = update_book(
        dbsession,
        author_id=account.id,
        book_id=book.id,
        payload=BookUpdateSchema(flavour="maxi"),
    )
    assert len(book.issues) == 0


@pytest.mark.parametrize(
    "book_flavour, title_flavours, expected",
    [
        pytest.param(None, ["maxi"], True),
        pytest.param("maxi", ["maxi", "mini"], False),
        pytest.param("maxi", ["mini", "nopic"], True),
        pytest.param(None, [], False),
        pytest.param("maxi", [], True),
        pytest.param("", [], False),
        pytest.param("", ["maxi"], True),
    ],
)
def test_has_flavour_mismatch(
    book_flavour: str, title_flavours: list[str], *, expected: bool
):
    assert has_flavour_mismatch(book_flavour, title_flavours) is expected
