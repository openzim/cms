from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Warehouse, ZimfarmNotification
from cms_backend.utils.datetime import getnow


@dataclass(eq=True, frozen=True)
class FileLocation:
    warehouse_id: UUID
    path: Path
    filename: str


def create_book(
    session: OrmSession,
    *,
    book_id: UUID,
    article_count: int,
    media_count: int,
    size: int,
    zim_metadata: dict[str, Any],
    zimcheck_result: dict[str, Any],
    zimfarm_notification: ZimfarmNotification,
) -> Book:
    """Create a new book"""

    # Extract metadata fields (optional fields may not be present)
    name = zim_metadata.get("Name")
    date = zim_metadata.get("Date")
    flavour = zim_metadata.get("Flavour")

    book = Book(
        id=book_id,
        created_at=getnow(),
        article_count=article_count,
        media_count=media_count,
        size=size,
        zim_metadata=zim_metadata,
        zimcheck_result=zimcheck_result,
        name=name,
        date=date,
        flavour=flavour,
        zimfarm_notification=zimfarm_notification,
    )
    session.add(book)
    zimfarm_notification.events.append(
        f"{getnow()}: notification transformed into book"
    )
    book.events.append(
        f"{getnow()}: created from Zimfarm notification {zimfarm_notification.id}"
    )

    return book


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


def get_next_book_to_move_files_or_none(
    session: OrmSession,
) -> Book | None:
    return session.scalars(
        select(Book)
        .where(
            Book.needs_file_operation.is_(True),
            Book.has_error.is_(False),
            Book.location_kind.not_in(["to_delete", "deleted"]),
        )
        .order_by(Book.created_at)
        .limit(1)
    ).one_or_none()


def get_next_book_to_process_or_none(
    session: OrmSession,
) -> Book | None:
    """Get next book that needs processing (not errored)."""
    return session.scalars(
        select(Book)
        .where(Book.needs_processing.is_(True))
        .where(Book.has_error.is_(False))
        .order_by(Book.created_at)
        .limit(1)
    ).one_or_none()
