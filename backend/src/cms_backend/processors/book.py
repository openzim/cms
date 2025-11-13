from uuid import UUID

from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.book import create_book_location
from cms_backend.db.models import Book, Title, TitleWarehousePath
from cms_backend.db.title import get_title_by_name_and_producer_or_none
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import compute_target_filename


def check_book_qa(book: Book) -> bool:
    try:
        missing_metadata_keys = [
            key
            for key in sorted(
                [
                    "Name",
                    "Title",
                    "Creator",
                    "Publisher",
                    "Date",
                    "Description",
                    "Language",
                ]
            )
            if key not in book.zim_metadata
        ]

        if missing_metadata_keys:
            book.events.append(
                f"{getnow()}: book is missing mandatory metadata: "
                f"{','.join(missing_metadata_keys)}"
            )
            book.status = "qa_failed"
            return False

        book.events.append(f"{getnow()}: book passed QA checks")
        return True

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while checking book QA\n{exc}"
        )
        logger.exception(f"Failed to check book QA for {book.id}")
        book.status = "errored"
        return False


def get_matching_title(session: ORMSession, book: Book) -> Title | None:
    try:
        if not book.name:
            book.events.append(
                f"{getnow()}: no title can be found because name is missing"
            )
            book.status = "qa_failed"
            return None

        title = get_title_by_name_and_producer_or_none(
            session, name=book.name, producer_unique_id=book.producer_unique_id
        )

        if not title:
            book.events.append(f"{getnow()}: no matching title found for book")
            book.status = "pending_title"
            return None

        book.events.append(f"{getnow()}: found matching title {title.id}")
        return title

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while get matching title\n{exc}"
        )
        logger.exception(f"Failed to get matching title for {book.id}")
        book.status = "errored"
        return None


def _current_locations_match_targets(
    book: Book,
    target_locations: list[tuple[UUID, str]],
) -> bool:
    """Check if book's current locations exactly match the target locations.

    Args:
        book: The book to check
        target_locations: List of (warehouse_path_id, filename) tuples representing
          target locations

    Returns:
        True if the set of current locations is strictly identical to target locations
    """
    # Extract current locations as set of (warehouse_path_id, filename) tuples
    current_set = {
        (loc.warehouse_path_id, loc.filename)
        for loc in book.locations
        if loc.status == "current"
    }

    # Convert target list to set
    target_set = set(target_locations)

    # Must be strictly identical
    return current_set == target_set


def create_book_target_locations(
    session: ORMSession,
    book: Book,
    target_warehouse_paths: list[TitleWarehousePath],
) -> None:
    """Create target locations for a book if not already at expected locations.

    Computes target locations based on the provided warehouse paths and filename,
    then checks if the book's current locations already match. If they do, no new
    target locations are created. Otherwise, target locations are created for each
    warehouse path.

    Args:
        session: SQLAlchemy session
        book: Book to create target locations for
        target_warehouse_paths: List of TitleWarehousePath objects defining where the
          book should be

    Side effects:
        - Adds event to book if targets already match current locations
        - Creates BookLocation records if targets don't match current locations
    """

    if not book.name:
        raise Exception("book name is missing or invalid")

    if not book.date:
        raise Exception("book date is missing or invalid")

    # Compute target filename once for this book
    target_filename = compute_target_filename(
        session,
        name=book.name,
        flavour=book.flavour,
        date=book.date,
        book_id=book.id,
    )

    # Compute all target locations as (warehouse_path_id, filename) tuples
    target_locations = [
        (title_warehouse_path.warehouse_path_id, target_filename)
        for title_warehouse_path in target_warehouse_paths
    ]

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
    for title_warehouse_path in target_warehouse_paths:
        create_book_location(
            session=session,
            book=book,
            warehouse_path_id=title_warehouse_path.warehouse_path_id,
            filename=target_filename,
            status="target",
        )

    book.status = "pending_move"
