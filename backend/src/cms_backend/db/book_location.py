from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Warehouse
from cms_backend.schemas.models import FileLocation
from cms_backend.utils.datetime import getnow


def create_book_location(
    session: OrmSession,
    *,
    book: Book,
    warehouse_id: UUID,
    path: Path,
    filename: str,
    status: str = "current",
) -> BookLocation:
    """Create a new book location.

    Args:
        session: SQLAlchemy session
        book: Book instance
        warehouse_id: ID of the warehouse
        path: Folder path within the warehouse (e.g., "dev-zim")
        filename: Filename in warehouse
        status: Location status ('current' or 'target'), defaults to 'current'

    Returns:
        Created BookLocation instance
    """
    # Get warehouse info for event message
    warehouse = session.get(Warehouse, warehouse_id)
    if not warehouse:
        raise ValueError(f"Warehouse with id {warehouse_id} not found")

    warehouse_name = warehouse.name

    location = BookLocation(
        book_id=book.id,
        warehouse_id=warehouse_id,
        path=path,
        status=status,
        filename=filename,
    )
    session.add(location)
    book.locations.append(location)
    book.events.append(
        f"{getnow()}: added {status} location: {filename} in {warehouse_name}: "
        f"{path} ({warehouse_id})"
    )

    return location


def current_locations_match_targets(
    book: Book,
    target_locations: list[FileLocation],
) -> bool:
    """Check if book's current locations exactly match the target locations.

    Args:
        book: The book to check
        target_locations: List of file locations representing target locations

    Returns:
        True if the set of current locations is strictly identical to target locations
    """
    # Extract current locations as set of (warehouse_id, path, filename) tuples
    current_set = {
        FileLocation(
            warehouse_id=loc.warehouse_id, path=loc.path, filename=loc.filename
        )
        for loc in book.locations
        if loc.status == "current"
    }

    # Convert target list to set
    target_set = set(target_locations)

    # Must be strictly identical
    return current_set == target_set


def create_book_target_locations(
    session: OrmSession,
    book: Book,
    target_locations: list[FileLocation],
) -> None:
    """Create target locations for a book if not already at expected locations.

    Computes target locations based on the provided warehouse paths and filename,
    then checks if the book's current locations already match. If they do, no new
    target locations are created. Otherwise, target locations are created for each
    warehouse path.

    Args:
        session: SQLAlchemy session
        book: Book to create target locations for
        target_locations: List of FileLocation where the book should be

    Side effects:
        - Adds event to book if targets already match current locations
        - Creates BookLocation records if targets don't match current locations
        - Updates book needs_file_operation flag
    """

    if not book.name:
        raise Exception("book name is missing or invalid")

    if not book.date:
        raise Exception("book date is missing or invalid")

    # Check if current locations already match targets exactly
    if current_locations_match_targets(book, target_locations):
        # Book is already at all expected locations - skip creating targets
        book.events.append(
            f"{getnow()}: book already at all target locations, skipping target "
            "creation"
        )
        book.needs_file_operation = False
        return

    # Create target locations for each applicable warehouse path
    for target_location in target_locations:
        create_book_location(
            session=session,
            book=book,
            warehouse_id=target_location.warehouse_id,
            path=target_location.path,
            filename=target_location.filename,
            status="target",
        )

    book.needs_file_operation = True
