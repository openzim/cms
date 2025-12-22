from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import create_book_location
from cms_backend.db.models import Book, Title
from cms_backend.mill.context import Context as MillContext
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import compute_target_filename


@dataclass(eq=True, frozen=True)
class FileLocation:
    warehouse_id: UUID
    path: Path
    filename: str


def add_book_to_title(session: OrmSession, book: Book, title: Title):
    try:
        # Retrieve name from book.name directly
        if not book.name:
            raise Exception("book name is missing or invalid")

        # Validate book.date is also present and valid
        if not book.date:
            raise Exception("book date is missing or invalid")

        title.books.append(book)
        book.events.append(f"{getnow()}: book added to title {title.id}")
        title.events.append(f"{getnow()}: book {book.id} added to title")

        # Update title name should it have changed (e.g. stackexchange domain updated
        # leading to ZIM name automatically updated as well)
        if title.name != book.name:
            title.events.append(f"{getnow()}: updating title name to {book.name}")
            title.name = book.name

        # Compute target filename once for this book
        target_filename = compute_target_filename(
            session,
            name=book.name,
            flavour=book.flavour,
            date=book.date,
            book_id=book.id,
        )

        # For now, only 'robust' maturity move straight to prod,
        # other maturity moves through staging first
        target_locations = (
            [
                FileLocation(
                    MillContext.staging_warehouse_id,
                    MillContext.staging_base_path,
                    target_filename,
                )
            ]
            if title.maturity != "robust"
            else [
                FileLocation(tc.collection.warehouse_id, tc.path, target_filename)
                for tc in title.collections
            ]
        )

        # Create target locations if not already at expected locations
        create_book_target_locations(
            session=session,
            book=book,
            target_locations=target_locations,
        )

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while adding to title {title.id}\n{exc}"
        )
        title.events.append(
            f"{getnow()}: error encountered while adding book {book.id}\n{exc}"
        )
        book.status = "errored"
        logger.exception(f"Failed to add book {book.id} to title {title.id}")


def _current_locations_match_targets(
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
    """

    if not book.name:
        raise Exception("book name is missing or invalid")

    if not book.date:
        raise Exception("book date is missing or invalid")

    # Check if current locations already match targets exactly
    if _current_locations_match_targets(book, target_locations):
        # Book is already at all expected locations - skip creating targets
        book.events.append(
            f"{getnow()}: book already at all target locations, skipping target "
            "creation"
        )
        book.status = "published"
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

    book.status = "pending_move"
