from collections.abc import Callable

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.book import create_book as db_create_book
from cms_backend.db.book import get_differing_metadata_keys, update_book
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Book, Title, ZimfarmNotification


def test_create_book(
    dbsession: OrmSession, zimfarm_notification: ZimfarmNotification, faker: Faker
):
    """Create a book from a zimfarm notification"""
    book_id = zimfarm_notification.id  # Use zimfarm notification ID as book ID
    book = db_create_book(
        dbsession,
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


def test_update_deleted_book(dbsession: OrmSession, create_book: Callable[..., Book]):
    book = create_book(location_kind="deleted")
    with pytest.raises(RecordDoesNotExistError, match=r"Book .* is already deleted"):
        update_book(dbsession, book.id, flavour="maxi")


def test_update_book_belonging_to_archived_title(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    book = create_book()
    title = create_title(archived=True)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"Book title .* is currently archived"):
        update_book(dbsession, book.id, flavour="maxi")


def test_update_book_with_same_flavour(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    book = create_book(flavour="maxi")
    assert book.flavour is not None
    update_book(dbsession, book.id, flavour=book.flavour)
    assert len(book.events) == 0


def test_update_book_with_different_flavour(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    book = create_book(flavour="maxi")
    assert book.flavour is not None
    book = update_book(dbsession, book.id, flavour="mini")
    assert book.flavour == "mini"
    assert len(book.events) == 1
    assert any("flavour updated from" in event for event in book.events)
