"""Tests for shuttle move_files module."""

from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Warehouse
from cms_backend.shuttle.move_files import move_book_files


def test_move_book_files_inaccessible_warehouse(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that move_book_files returns early if a warehouse is not accessible"""
    warehouse = create_warehouse(name="inaccessible_warehouse")
    book = create_book()
    book.needs_file_operation = True
    dbsession.flush()

    create_book_location(book=book, warehouse_id=warehouse.id)
    dbsession.flush()

    # Mock ShuttleContext with empty warehouse paths (no warehouses accessible)
    with patch("cms_backend.shuttle.move_files.ShuttleContext") as mock_context:
        mock_context.local_warehouse_paths = {}

        move_book_files(dbsession, book)

    assert book.has_error is False
    assert book.needs_processing is False
    assert book.needs_file_operation is True
    assert len(book.events) == 0


def test_move_book_files_no_current_location(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that move_book_files errors if there's no current location"""
    warehouse = create_warehouse()
    book = create_book()
    book.needs_file_operation = True
    dbsession.flush()

    # Create a target location but no current location
    book_location = BookLocation(
        book_id=book.id,
        warehouse_id=warehouse.id,
        path=Path("target_path"),
        filename="test.zim",
        status="target",
    )
    dbsession.add(book_location)
    dbsession.flush()

    with patch("cms_backend.shuttle.move_files.ShuttleContext") as mock_context:
        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}

        move_book_files(dbsession, book)

    assert book.has_error is True
    assert book.needs_processing is False
    assert book.needs_file_operation is True
    assert any("no current location" in event for event in book.events)


def test_move_book_files_no_target_location(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that move_book_files marks book as published if there's
    no target location"""
    warehouse = create_warehouse()
    book = create_book()
    book.needs_file_operation = True
    dbsession.flush()

    create_book_location(book=book, warehouse_id=warehouse.id, status="current")
    dbsession.flush()

    with patch("cms_backend.shuttle.move_files.ShuttleContext") as mock_context:
        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}

        move_book_files(dbsession, book)

    assert book.needs_processing is False
    assert book.has_error is False
    assert book.needs_file_operation is False
    assert any("no target location set" in event for event in book.events)


def test_move_book_files_copy_operation(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that move_book_files performs copy when more targets than current"""
    warehouse = create_warehouse()
    book = create_book()
    book.needs_file_operation = True
    dbsession.flush()

    # One current location
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="current", status="current"
    )

    # Two target locations
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="target1", status="target"
    )
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="target2", status="target"
    )
    dbsession.flush()

    with ExitStack() as stack:
        mock_context = stack.enter_context(
            patch("cms_backend.shuttle.move_files.ShuttleContext")
        )
        mock_copy = stack.enter_context(patch("shutil.copy"))
        stack.enter_context(patch("shutil.move"))
        stack.enter_context(patch("pathlib.Path.mkdir"))

        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}
        move_book_files(dbsession, book)

        # Should have copied once (target_loc2 > current_loc)
        assert mock_copy.call_count == 1

    assert book.needs_processing is False
    assert book.has_error is False
    assert book.needs_file_operation is False
    assert any("copied book from" in event for event in book.events)
    # One target should now be current
    assert sum(1 for loc in book.locations if loc.status == "current") >= 1


def test_move_book_files_move_operation(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that move_book_files performs move when targets equal current"""
    warehouse = create_warehouse()
    book = create_book()
    book.needs_file_operation = True
    dbsession.flush()

    # One current location
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="current", status="current"
    )

    # One target location
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="target", status="target"
    )
    dbsession.flush()

    with ExitStack() as stack:
        mock_context = stack.enter_context(
            patch("cms_backend.shuttle.move_files.ShuttleContext")
        )
        mock_move = stack.enter_context(patch("shutil.move"))
        stack.enter_context(patch("pathlib.Path.mkdir"))

        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}
        move_book_files(dbsession, book)

        # Should have moved once
        assert mock_move.call_count == 1

    assert book.needs_processing is False
    assert book.has_error is False
    assert book.needs_file_operation is False
    assert any("moved book from" in event for event in book.events)
    # Current location should be removed
    assert len([loc for loc in book.locations if loc.status == "current"]) == 1


def test_move_book_files_delete_operation(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that move_book_files deletes extra current locations"""
    warehouse = create_warehouse()
    book = create_book()
    book.needs_file_operation = True
    dbsession.flush()

    # Two current locations
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="current1", status="current"
    )
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="current2", status="current"
    )

    # One target location
    create_book_location(
        book=book, warehouse_id=warehouse.id, path="target", status="target"
    )
    dbsession.flush()

    with ExitStack() as stack:
        mock_context = stack.enter_context(
            patch("cms_backend.shuttle.move_files.ShuttleContext")
        )
        stack.enter_context(patch("shutil.move"))
        stack.enter_context(patch("pathlib.Path.mkdir"))
        mock_unlink = stack.enter_context(patch("pathlib.Path.unlink"))

        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}
        move_book_files(dbsession, book)

        # Should have deleted one extra location
        assert mock_unlink.call_count == 1

    assert book.needs_processing is False
    assert book.has_error is False
    assert book.needs_file_operation is False
    assert any("deleted old location" in event for event in book.events)


def test_move_book_files_updates_book_locations(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that move_book_files updates target locations to current status"""
    warehouse = create_warehouse()
    book = create_book()
    book.needs_file_operation = True
    dbsession.flush()

    # One current location
    _current_loc = create_book_location(
        book=book, warehouse_id=warehouse.id, path="current", status="current"
    )

    # One target location
    _target_loc = create_book_location(
        book=book, warehouse_id=warehouse.id, path="target", status="target"
    )
    dbsession.flush()

    with ExitStack() as stack:
        mock_context = stack.enter_context(
            patch("cms_backend.shuttle.move_files.ShuttleContext")
        )
        stack.enter_context(patch("shutil.move"))
        stack.enter_context(patch("pathlib.Path.mkdir"))

        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}
        move_book_files(dbsession, book)

    # After move, target should become current
    assert _target_loc.status == "current"
    # Old current should be removed from book.locations
    assert _current_loc not in book.locations
