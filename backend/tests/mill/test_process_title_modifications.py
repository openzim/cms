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


def test_process_title_modifications_processes_matching_book(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
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
