from collections.abc import Callable
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Warehouse
from cms_backend.shuttle.delete_files import delete_book_files, delete_files
from cms_backend.utils.datetime import getnow


def test_delete_files_processes_eligible_book(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that delete_files processes books ready for deletion."""
    warehouse = create_warehouse()
    now = getnow()

    book = create_book()
    book.location_kind = "to_delete"
    book.deletion_date = now - timedelta(days=1)
    book.has_error = False
    book.needs_file_operation = True
    dbsession.flush()

    create_book_location(book=book, warehouse_id=warehouse.id, status="current")
    dbsession.flush()

    with ExitStack() as stack:
        mock_context = stack.enter_context(
            patch("cms_backend.shuttle.delete_files.ShuttleContext")
        )
        stack.enter_context(patch("pathlib.Path.unlink"))

        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}

        delete_files(dbsession)

    assert book.location_kind == "deleted"
    assert book.needs_file_operation is False


def test_delete_files_inaccessible_warehouse(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that delete_files skips books if warehouse is not accessible."""
    warehouse = create_warehouse(name="inaccessible_warehouse")
    now = getnow()

    book = create_book()
    book.location_kind = "to_delete"
    book.deletion_date = now - timedelta(days=1)
    book.has_error = False
    book.needs_file_operation = True
    dbsession.flush()

    create_book_location(book=book, warehouse_id=warehouse.id, status="current")
    dbsession.flush()

    with patch("cms_backend.shuttle.delete_files.ShuttleContext") as mock_context:
        mock_context.local_warehouse_paths = {}
        delete_book_files(dbsession, book)

    assert book.location_kind == "to_delete"
    assert book.needs_file_operation is True
    assert len(book.events) == 0


def test_delete_files_handles_file_deletion_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that delete_files handles file deletion errors gracefully."""
    warehouse = create_warehouse()
    now = getnow()

    book = create_book()
    book.location_kind = "to_delete"
    book.deletion_date = now - timedelta(days=1)
    book.has_error = False
    book.needs_file_operation = True
    dbsession.flush()

    create_book_location(
        book=book, warehouse_id=warehouse.id, path="path", status="current"
    )
    dbsession.flush()

    with ExitStack() as stack:
        mock_context = stack.enter_context(
            patch("cms_backend.shuttle.delete_files.ShuttleContext")
        )
        mock_unlink = stack.enter_context(patch("pathlib.Path.unlink"))

        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}
        mock_unlink.side_effect = OSError("Permission denied")

        delete_files(dbsession)

    # Book should be marked with error
    assert book.has_error is True
    assert book.location_kind == "to_delete"
    assert any(
        "error encountered while deleting files" in event for event in book.events
    )


def test_delete_files_handles_errors_and_continues_processing(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that delete_files marks books with errors and continues."""
    warehouse = create_warehouse()
    now = getnow()

    # Create two eligible books
    book1 = create_book()
    book1.location_kind = "to_delete"
    book1.deletion_date = now - timedelta(days=1)
    book1.has_error = False
    book1.needs_file_operation = True

    book2 = create_book()
    book2.location_kind = "to_delete"
    book2.deletion_date = now - timedelta(days=2)
    book2.has_error = False
    book2.needs_file_operation = True

    dbsession.flush()

    create_book_location(book=book1, warehouse_id=warehouse.id, status="current")
    create_book_location(book=book2, warehouse_id=warehouse.id, status="current")
    dbsession.flush()

    with ExitStack() as stack:
        mock_context = stack.enter_context(
            patch("cms_backend.shuttle.delete_files.ShuttleContext")
        )
        mock_unlink = stack.enter_context(patch("pathlib.Path.unlink"))

        mock_context.local_warehouse_paths = {warehouse.id: Path("/warehouse")}

        # Make unlink fail for the first call only
        mock_unlink.side_effect = [OSError("Permission denied"), None]

        delete_files(dbsession)

    # book2 is processed first (older deletion_date) and should have error
    assert book2.has_error is True
    assert any(
        "error encountered while deleting files" in event for event in book2.events
    )

    # book1 is processed second and should succeed
    assert book1.location_kind == "deleted"
    assert book1.has_error is False
