"""Tests for book processor."""

from collections.abc import Callable
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, Title
from cms_backend.mill.processors.book import (
    check_book_zim_spec,
    get_matching_title,
    process_book,
)

MINIMUM_ZIM_METADATA = {
    "Name": "test_en_all",
    "Title": "A superb ZIM",
    "Creator": "openZIM",
    "Publisher": "openZIM",
    "Date": "2025-10-01",
    "Description": "About a super content",
    "Language": "eng",
}

GOOD_ZIM_METADATA = {
    **MINIMUM_ZIM_METADATA,
    "Long description": "X" * 100,
    "Flavour": "nopic",
}


def test_check_book_zim_spec_with_good_metadata(
    create_book: Callable[..., Book],
):
    """Test that book with all mandatory metadata passes ZIM spec check"""
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)

    assert check_book_zim_spec(book) is True
    assert any("passed ZIM specification checks" in event for event in book.events)


def test_check_book_zim_spec_missing_metadata(
    create_book: Callable[..., Book],
):
    """Test that book with missing mandatory metadata fails ZIM spec check"""
    # Missing "Title"
    metadata = {k: v for k, v in GOOD_ZIM_METADATA.items() if k != "Title"}
    book = create_book(zim_metadata=metadata)

    assert check_book_zim_spec(book) is False
    assert book.has_error is True
    assert any(
        "missing mandatory metadata" in event and "Title" in event
        for event in book.events
    )


def test_check_book_zim_spec_empty_metadata_value(
    create_book: Callable[..., Book],
):
    """Test that book with empty mandatory metadata value fails ZIM spec check"""
    metadata = GOOD_ZIM_METADATA.copy()
    metadata["Title"] = ""  # Empty string
    book = create_book(zim_metadata=metadata)

    assert check_book_zim_spec(book) is False
    assert book.has_error is True
    assert any(
        "missing mandatory metadata" in event and "Title" in event
        for event in book.events
    )


def test_get_matching_title_with_matching_title(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
):
    """Test that get_matching_title finds a title by book name"""
    title = create_title(name="test_en_all")
    dbsession.flush()

    book = create_book(zim_metadata=GOOD_ZIM_METADATA)

    found_title = get_matching_title(dbsession, book)

    assert found_title is not None
    assert found_title.id == title.id
    assert any(f"found matching title {title.id}" in event for event in book.events)


def test_get_matching_title_no_match(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that get_matching_title returns None when no title matches"""
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    dbsession.flush()

    # No title with this name exists
    found_title = get_matching_title(dbsession, book)

    assert found_title is None
    assert any("no matching title found for book" in event for event in book.events)


def test_get_matching_title_missing_book_name(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that get_matching_title handles missing book name"""
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    book.name = None  # Simulate missing name
    dbsession.flush()

    found_title = get_matching_title(dbsession, book)

    assert found_title is None
    assert book.has_error is True
    assert any(
        "no title can be found because name is missing" in event
        for event in book.events
    )


def test_process_book_with_matching_title(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
):
    """Test that process_book calls add_book_to_title when title is found"""
    title = create_title(name="test_en_all")
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    dbsession.flush()

    with patch("cms_backend.mill.processors.book.add_book_to_title") as mock_add:
        process_book(dbsession, book)

    # Should have passed ZIM spec check
    assert any("passed ZIM specification checks" in event for event in book.events)

    # Should have found title
    assert any(f"found matching title {title.id}" in event for event in book.events)

    # Should have called add_book_to_title
    mock_add.assert_called_once()
    assert mock_add.call_args[0][1] == book
    assert mock_add.call_args[0][2].id == title.id


def test_process_book_bad_zim_spec(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that process_book stops if ZIM spec check fails"""
    # Missing Title
    metadata = {k: v for k, v in GOOD_ZIM_METADATA.items() if k != "Title"}
    book = create_book(zim_metadata=metadata)
    book.needs_processing = True
    dbsession.flush()

    with patch("cms_backend.mill.processors.book.add_book_to_title") as mock_add:
        process_book(dbsession, book)

    # Should have failed ZIM spec check
    assert book.has_error is True
    assert book.needs_processing is False

    # Should NOT have called add_book_to_title
    mock_add.assert_not_called()


def test_process_book_no_matching_title(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Test that process_book stops if no matching title is found"""
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    dbsession.flush()

    with patch("cms_backend.mill.processors.book.add_book_to_title") as mock_add:
        process_book(dbsession, book)

    # Should have passed ZIM spec check
    assert any("passed ZIM specification checks" in event for event in book.events)

    # Should have no matching title
    assert book.needs_processing is False
    assert book.has_error is False
    assert book.needs_file_operation is False

    # Should NOT have called add_book_to_title
    mock_add.assert_not_called()
