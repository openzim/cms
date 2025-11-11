import re
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, Title
from cms_backend.processors.book import check_book_qa, get_matching_title

MINIMUM_ZIM_METADATA = {
    "Name": "test_en_all",
    "Title": "A superb ZIM",
    "Creator": "openZIM",
    "Publisher": "openZIM",
    "Date": "2025-10-01",
    "Description": "About a super content",
    "Language": "eng",
}

# minimum set of metadata + a long description + a flavour + a random one
GOOD_ZIM_METADATA = {
    **MINIMUM_ZIM_METADATA,
    "Long description": "X" * 100,
    "Flavour": "nopic",
    "Foo": "Bar",
}


def test_check_book_qa_ok(create_book: Callable[..., Book]):
    """Check book QA - all is good"""

    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    assert len(book.events) == 0
    book_qa = check_book_qa(book=book)
    assert book_qa is True
    assert any(
        event for event in book.events if re.match(".*: book passed QA checks", event)
    )


@pytest.mark.parametrize(
    "missing_key, book_metadata",
    [
        pytest.param(
            missing_key,
            {
                key: value
                for key, value in GOOD_ZIM_METADATA.items()
                if key != missing_key
            },
            id=f"missing-{missing_key}",
        )
        for missing_key in MINIMUM_ZIM_METADATA.keys()
    ],
)
def test_check_book_qa_missing_mandatory(
    create_book: Callable[..., Book], missing_key: str, book_metadata: dict[str, Any]
):
    """Check book QA - one mandatory key is missing"""

    book = create_book(zim_metadata=book_metadata)
    assert len(book.events) == 0
    book_qa = check_book_qa(book=book)
    assert book_qa is False
    assert any(
        event
        for event in book.events
        if re.match(f".*: book is missing mandatory metadata: {missing_key}", event)
    )


def test_check_book_qa_missing_multiple_mandatory(create_book: Callable[..., Book]):
    """Check book QA - one mandatory key is missing"""

    book = create_book(
        zim_metadata={
            key: value
            for key, value in GOOD_ZIM_METADATA.items()
            if key not in ("Description", "Title")
        }
    )
    assert len(book.events) == 0
    book_qa = check_book_qa(book=book)
    assert book_qa is False
    assert any(
        event
        for event in book.events
        if re.match(".*: book is missing mandatory metadata: Description,Title", event)
    )


def test_check_book_qa_bad_error(create_book: Callable[..., Book]):
    """Get matching title for a given book - bad error occurs"""

    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    assert len(book.events) == 0
    # simulate a very bad error by dropping an expected property (and adding it back so
    # that SQLAlchemy does not choke)
    save_metadata = book.zim_metadata
    del book.zim_metadata
    book_qa = check_book_qa(book=book)
    book.zim_metadata = save_metadata
    assert book_qa is False
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while checking book QA", event)
    )


def test_get_matching_title_found(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - title exist"""

    book = create_book(name=title.name, producer_unique_id=title.producer_unique_id)
    assert len(book.events) == 0
    assert len(title.events) == 0
    matching_title = get_matching_title(dbsession, book=book)
    assert matching_title == title
    assert any(
        event for event in book.events if re.match(".*: found matching title .*", event)
    )
    assert len(title.events) == 0


def test_get_matching_title_not_found(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - title does not exist"""

    book_name = "test2_fr_all"
    assert book_name != title.name
    book = create_book(name=book_name)
    assert len(book.events) == 0
    assert len(title.events) == 0
    matching_title = get_matching_title(dbsession, book=book)
    assert matching_title is None
    assert any(
        event
        for event in book.events
        if re.match(".*: no matching title found for book", event)
    )
    assert len(title.events) == 0


def test_get_matching_title_no_name(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - book has an empty Name"""

    book_name = ""
    assert book_name != title.name
    book = create_book(name=book_name)
    assert len(book.events) == 0
    assert len(title.events) == 0
    matching_title = get_matching_title(dbsession, book=book)
    assert matching_title is None
    assert any(
        event
        for event in book.events
        if re.match(".*: no title can be found because name is missing", event)
    )
    assert len(title.events) == 0


def test_get_matching_title_bad_error(
    dbsession: OrmSession, create_book: Callable[..., Book], title: Title
):
    """Get matching title for a given book - bad error occurs"""

    book = create_book(name=title.name)
    assert len(book.events) == 0
    assert len(title.events) == 0
    # simulate a very bad error by dropping an expected property (and adding it back so
    # that SQLAlchemy does not choke)
    save_producer_unique_id = book.producer_unique_id
    del book.producer_unique_id
    matching_title = get_matching_title(dbsession, book=book)
    book.producer_unique_id = save_producer_unique_id
    assert matching_title is None
    assert any(
        event
        for event in book.events
        if re.match(".*: error encountered while get matching title", event)
    )
    assert len(title.events) == 0
