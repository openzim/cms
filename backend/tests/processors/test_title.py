import re
from collections.abc import Callable

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, Title
from cms_backend.processors.title import add_book_to_title


def test_add_book_to_title_same_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with same name"""

    book = create_book(zim_metadata={"Name": title.name})
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(book=book, title=title)
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
    book = create_book(zim_metadata={"Name": book_name})
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(book=book, title=title)
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
    book = create_book(zim_metadata={"Name": book_name})
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(book=book, title=title)
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


def test_add_book_to_title_bad_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Add a book to an existing title with a bad type name"""

    book_name = 123  # integer instead of string
    assert book_name != title.name
    book = create_book(zim_metadata={"Name": book_name})
    assert len(book.events) == 0
    assert len(title.events) == 0
    add_book_to_title(book=book, title=title)
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

    book = create_book(zim_metadata={"Name": title.name})
    assert len(book.events) == 0
    assert len(title.events) == 0

    # simulate a very bad error by dropping an expected property (and adding it back so
    # that SQLAlchemy does not choke)
    save_metadata = book.zim_metadata
    del book.zim_metadata
    add_book_to_title(book=book, title=title)
    book.zim_metadata = save_metadata

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
