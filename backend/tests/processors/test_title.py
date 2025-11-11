import re
from collections.abc import Callable

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, Title
from cms_backend.processors.title import add_book_to_title


def test_add_book_to_title_same_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with same name"""

    book = create_book(name=title.name, date="2024-01-01")
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(session=dbsession, book=book, title=title)
    dbsession.flush()
    assert book.title == title
    assert book.title_id == title.id
    assert book in title.books
    assert any(
        event for event in title.events if re.match(".*: book .* added to title", event)
    )
    assert any(
        event for event in book.events if re.match(".*: book added to title .*", event)
    )


def test_add_book_to_title_different_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with different name"""

    book_name = "test2_fr_all"
    assert book_name != title.name
    book = create_book(name=book_name, date="2024-01-01")
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(session=dbsession, book=book, title=title)
    dbsession.flush()
    assert book.title == title
    assert book.title_id == title.id
    assert book in title.books
    assert title.name == book_name  # title name has been overriden
    assert any(
        event for event in title.events if re.match(".*: book .* added to title", event)
    )
    assert any(
        event
        for event in title.events
        if re.match(f".*: updating title name to {book_name}", event)
    )
    assert any(
        event for event in book.events if re.match(".*: book added to title .*", event)
    )


def test_add_book_to_title_empty_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with an empty name"""

    book_name = ""
    assert book_name != title.name
    book = create_book(name=book_name, date="2024-01-01")
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(session=dbsession, book=book, title=title)
    dbsession.flush()
    assert book not in title.books
    assert book.title is None
    assert book.title_id is None
    assert [
        event for event in title.events if re.match(".*: book .* added to title", event)
    ] == []
    assert [
        event for event in book.events if re.match(".*: book added to title .*", event)
    ] == []
    assert any(
        event
        for event in title.events
        if re.match(".*: error encountered while adding book .*", event)
    )
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while adding to title .*", event)
    )


def test_add_book_to_title_missing_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with missing name"""

    book = create_book(name=None, date="2024-01-01")
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(session=dbsession, book=book, title=title)
    dbsession.flush()
    assert book not in title.books
    assert book.title is None
    assert book.title_id is None
    assert [
        event for event in title.events if re.match(".*: book .* added to title", event)
    ] == []
    assert [
        event for event in book.events if re.match(".*: book added to title .*", event)
    ] == []
    assert any(
        event
        for event in title.events
        if re.match(".*: error encountered while adding book .*", event)
    )
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while adding to title .*", event)
    )


def test_add_book_to_title_bad_error(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title which encounters a bad error"""

    book = create_book(name=title.name, date="2024-01-01")
    assert len(book.events) == 0
    assert len(title.events) == 0

    # simulate a very bad error by dropping an expected property (and adding it back so
    # that SQLAlchemy does not choke)
    save_name = book.name
    book.name = None
    add_book_to_title(session=dbsession, book=book, title=title)
    book.name = save_name

    dbsession.flush()
    assert book not in title.books
    assert book.title is None
    assert book.title_id is None
    assert [
        event for event in title.events if re.match(".*: book .* added to title", event)
    ] == []
    assert [
        event for event in book.events if re.match(".*: book added to title .*", event)
    ] == []
    assert any(
        event
        for event in title.events
        if re.match(".*: error encountered while adding book .*", event)
    )
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while adding to title .*", event)
    )


def test_add_book_to_title_updates_producer_fields(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
):
    """Add a book to a title updates producer display fields"""

    # Create a title without producer display fields (only unique_id)
    title = create_title(
        name="test_en_all",
        producer_unique_id="550e8400-e29b-41d4-a716-446655440000",
        producer_display_name=None,
        producer_display_url=None,
    )

    # Create a book with complete producer information
    book = create_book(
        name=title.name,
        date="2024-01-01",
        producer_unique_id=title.producer_unique_id,
        producer_display_name="farm.openzim.org: test_en_all",
        producer_display_url="https://farm.openzim.org/recipes/test_en_all",
    )

    assert title.producer_display_name is None
    assert title.producer_display_url is None
    assert len(book.events) == 0
    assert len(title.events) == 0

    add_book_to_title(session=dbsession, book=book, title=title)
    dbsession.flush()

    # Verify producer fields were updated
    assert title.producer_display_name == book.producer_display_name
    assert title.producer_display_url == book.producer_display_url
    assert any(
        event
        for event in title.events
        if re.match(".*: updating title producer_display_name to .*", event)
    )
    assert any(
        event
        for event in title.events
        if re.match(".*: updating title producer_display_url to .*", event)
    )


def test_add_book_to_title_missing_date(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with missing date"""

    book = create_book(name=title.name, date=None)
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(session=dbsession, book=book, title=title)
    dbsession.flush()
    assert book not in title.books
    assert book.title is None
    assert book.title_id is None
    assert [
        event for event in title.events if re.match(".*: book .* added to title", event)
    ] == []
    assert [
        event for event in book.events if re.match(".*: book added to title .*", event)
    ] == []
    assert any(
        event
        for event in title.events
        if re.match(".*: error encountered while adding book .*", event)
    )
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while adding to title .*", event)
    )


def test_add_book_to_title_empty_date(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with empty date"""

    book = create_book(name=title.name, date="")
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(session=dbsession, book=book, title=title)
    dbsession.flush()
    assert book not in title.books
    assert book.title is None
    assert book.title_id is None
    assert [
        event for event in title.events if re.match(".*: book .* added to title", event)
    ] == []
    assert [
        event for event in book.events if re.match(".*: book added to title .*", event)
    ] == []
    assert any(
        event
        for event in title.events
        if re.match(".*: error encountered while adding book .*", event)
    )
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while adding to title .*", event)
    )
