from collections.abc import Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.event import create_title_modified_event
from cms_backend.db.models import Book, Event, Title
from cms_backend.mill.process_title_modifications import process_title_modifications
from cms_backend.utils.datetime import getnow


def test_process_title_modifications_event_missing_keys(
    dbsession: OrmSession,
):
    """Test that events with missing keys are deleted"""
    event = Event(
        created_at=getnow(),
        topic="title_modified",
        payload={"id": str(uuid4()), "action": "created"},
    )
    dbsession.add(event)
    dbsession.flush()

    process_title_modifications(dbsession)

    assert (
        dbsession.scalars(select(Event).where(Event.id == event.id)).one_or_none()
        is None
    )


def test_process_title_modifications_title_does_not_exist(
    dbsession: OrmSession,
):
    """Test that events for non-existent titles are deleted"""
    event = create_title_modified_event(
        dbsession,
        action="created",
        title_name="non_existent_title",
        title_id=uuid4(),
    )
    process_title_modifications(dbsession)
    assert (
        dbsession.scalars(select(Event).where(Event.id == event.id)).one_or_none()
        is None
    )


def test_process_title_modifications_no_matching_books(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    """Test that events are deleted when no matching books exist"""
    title = create_title(name="wikipedia_en_all")
    event = create_title_modified_event(
        dbsession,
        action="created",
        title_name="wikipedia_en_all",
        title_id=title.id,
    )
    process_title_modifications(dbsession)
    assert (
        dbsession.scalars(select(Event).where(Event.id == event.id)).one_or_none()
        is None
    )


def test_process_title_modifications_skips_books_with_errors(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that books with errors are not processed"""
    title = create_title(name="wikipedia_en_all")

    # Create a book with has_error=True
    book = create_book(name="wikipedia_en_all", date="2024-01")
    book.has_error = True
    dbsession.add(book)

    event = create_title_modified_event(
        dbsession,
        action="created",
        title_name="wikipedia_en_all",
        title_id=title.id,
    )

    process_title_modifications(dbsession)

    # Event should be deleted (book has error)
    assert (
        dbsession.scalars(select(Event).where(Event.id == event.id)).one_or_none()
        is None
    )
    # Book should still not have a title
    dbsession.refresh(book)
    assert book.title_id is None


def test_process_title_modifications_skips_deleted_and_to_delete_books(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    illustration_48x48_at_1: str,
):
    """Test that books with location kinds delete and to_delete are not processed"""
    zim_metadata = {
        "Name": "wikipedia_en_all",
        "Title": "Wikipedia",
        "Creator": "Wikipedia Contributors",
        "Publisher": "Kiwix",
        "Date": "2025-01",
        "Description": "Wikipedia Encyclopedia",
        "Language": "eng",
        "Illustration_48x48@1": illustration_48x48_at_1,
    }
    title = create_title(name="wikipedia_en_all")

    book1 = create_book(
        name="wikipedia_en_all",
        date="2024-01",
        location_kind="deleted",
        zim_metadata=zim_metadata,
    )
    book2 = create_book(
        name="wikipedia_en_all",
        date="2024-01",
        location_kind="to_delete",
        zim_metadata=zim_metadata,
    )

    book3 = create_book(
        name="wikipedia_en_all", date="2024-01", zim_metadata=zim_metadata
    )

    dbsession.add_all([book1, book2, book3])

    create_title_modified_event(
        dbsession,
        action="created",
        title_name="wikipedia_en_all",
        title_id=title.id,
    )
    process_title_modifications(dbsession)

    dbsession.refresh(book1)
    assert book1.title_id is None

    dbsession.refresh(book2)
    assert book2.title_id is None

    dbsession.refresh(book3)
    assert book3.title_id == title.id


def test_process_title_modifications_processes_matching_book(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    illustration_48x48_at_1: str,
):
    """Test that matching books are processed"""
    title = create_title(name="wikipedia_en_all")

    # Create a book without a title
    book = create_book(
        name="wikipedia_en_all",
        date="2024-01",
        zim_metadata={
            "Name": "wikipedia_en_all",
            "Title": "Wikipedia",
            "Creator": "Wikipedia Contributors",
            "Publisher": "Kiwix",
            "Date": "2025-01",
            "Description": "Wikipedia Encyclopedia",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
    )
    book.has_error = False
    book.title_id = None
    dbsession.add(book)

    create_title_modified_event(
        dbsession,
        action="created",
        title_name="wikipedia_en_all",
        title_id=title.id,
    )
    process_title_modifications(dbsession)
    dbsession.refresh(book)
    assert book.title_id == title.id
