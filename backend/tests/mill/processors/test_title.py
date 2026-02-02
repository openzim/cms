"""Tests for title processor."""

from collections.abc import Callable
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, Collection, Title, Warehouse
from cms_backend.mill.processors.title import add_book_to_title

GOOD_ZIM_METADATA = {
    "Name": "test_en_all",
    "Title": "Test Article",
    "Creator": "openZIM",
    "Publisher": "openZIM",
    "Date": "2025-01-01",
    "Description": "Test description",
    "Language": "eng",
    "Flavour": "full",
}


def test_add_book_to_title_sets_events(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that add_book_to_title sets events on both book and title"""
    title = create_title(name="test_en_all")
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    dbsession.flush()

    with patch("cms_backend.mill.processors.title.create_book_target_locations"):
        add_book_to_title(dbsession, book, title)

    # Check book events
    assert any(f"book added to title {title.id}" in event for event in book.events)

    # Check title events
    assert any(f"book {book.id} added to title" in event for event in title.events)


def test_add_book_to_title_adds_book_to_relationship(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that add_book_to_title adds book to title.books relationship"""
    title = create_title(name="test_en_all")
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    dbsession.flush()

    # with patch("cms_backend.mill.processors.title.create_book_target_locations"):
    add_book_to_title(dbsession, book, title)

    assert book in title.books
    assert book.title_id == title.id
    assert book.needs_file_operation is True


def test_add_book_to_title_updates_title_name_when_different(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that add_book_to_title updates title name when book has different name"""
    title = create_title(name="old_name")
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)  # Name is "test_en_all"
    dbsession.flush()

    assert title.name == "old_name"
    assert book.name == "test_en_all"

    with patch("cms_backend.mill.processors.title.create_book_target_locations"):
        add_book_to_title(dbsession, book, title)

    # Title name should be updated
    assert title.name == "test_en_all"

    # Event should be logged
    assert any("updating title name to test_en_all" in event for event in title.events)


def test_add_book_to_title_no_update_when_name_same(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that add_book_to_title doesn't update title name when it's the same"""
    title = create_title(name="test_en_all")
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)  # Name is "test_en_all"
    dbsession.flush()

    with patch("cms_backend.mill.processors.title.create_book_target_locations"):
        add_book_to_title(dbsession, book, title)

    # Title name should remain the same
    assert title.name == "test_en_all"

    # No name update event should be logged
    assert not any("updating title name" in event for event in title.events)


def test_add_book_to_title_dev_maturity_staging(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that books for dev maturity titles are sent to staging"""
    title = create_title(name="test_en_all")
    title.maturity = "dev"  # Default, but explicit
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    dbsession.flush()

    with patch(
        "cms_backend.mill.processors.title.create_book_target_locations"
    ) as mock_create:
        add_book_to_title(dbsession, book, title)

    # Should have called create_book_target_locations with staging location
    mock_create.assert_called_once()
    target_locations = mock_create.call_args[1]["target_locations"]

    # Should be a single staging location
    assert len(target_locations) == 1
    assert target_locations[0].path.name == "staging"  # MillContext.staging_base_path


def test_add_book_to_title_robust_maturity_collections(
    dbsession: OrmSession,
    create_collection: Callable[..., Collection],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that books for robust maturity titles go directly to collection
    warehouses"""
    warehouse = create_warehouse()
    collection = create_collection(warehouse=warehouse)

    # Create a title and associate it with collection
    title = create_title(name="test_en_all")
    title.maturity = "robust"
    from pathlib import Path

    from cms_backend.db.models import CollectionTitle

    ct = CollectionTitle(path=Path("wikipedia"))
    ct.title = title
    ct.collection = collection
    dbsession.add(ct)
    dbsession.flush()

    book = create_book(zim_metadata=GOOD_ZIM_METADATA)

    with patch(
        "cms_backend.mill.processors.title.create_book_target_locations"
    ) as mock_create:
        add_book_to_title(dbsession, book, title)

    # Should have called create_book_target_locations with collection locations
    mock_create.assert_called_once()
    target_locations = mock_create.call_args[1]["target_locations"]

    # Should have one location per collection
    assert len(target_locations) == 1
    assert target_locations[0].warehouse_id == collection.warehouse_id


def test_add_book_to_title_missing_book_name(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that add_book_to_title handles missing book name"""
    title = create_title(name="test_en_all")
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    book.name = None  # Simulate missing name
    dbsession.flush()

    with patch("cms_backend.mill.processors.title.create_book_target_locations"):
        add_book_to_title(dbsession, book, title)

    # Should have error events
    assert any(
        f"error encountered while adding to title {title.id}" in event
        for event in book.events
    )
    assert any(
        f"error encountered while adding book {book.id}" in event
        for event in title.events
    )


def test_add_book_to_title_missing_book_date(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """Test that add_book_to_title handles missing book date"""
    title = create_title(name="test_en_all")
    book = create_book(zim_metadata=GOOD_ZIM_METADATA)
    book.date = None  # Simulate missing date
    dbsession.flush()

    with patch("cms_backend.mill.processors.title.create_book_target_locations"):
        add_book_to_title(dbsession, book, title)

    # Should have error events
    assert any(
        f"error encountered while adding to title {title.id}" in event
        for event in book.events
    )
