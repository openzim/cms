import datetime
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import create_book_location
from cms_backend.db.models import Book, Title
from cms_backend.mill.context import Context as MillContext
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import (
    PERIOD_LENGTH,
    compute_target_filename,
    get_period_and_suffix_from_filename,
)


@dataclass(eq=True, frozen=True)
class FileLocation:
    warehouse_id: UUID
    path: Path
    filename: str


def apply_retention_rules(session: OrmSession, title: Title):
    """Apply retention rules to `prod` books belonging to same title and flavour group.

    The retention rules are described in https://wiki.openzim.org/wiki/ZIM_Updates
    - Keep last version of two ZIM files from the two last distinct months (e.g
        if we have `2024-04`, `2024-04a`, `2024-06`, `2024-06a`, `2024-06b`,
        then we keep `2024-04a` and `2024-06b`)
    - AND keep every version which is 30 days old or less.
    """

    now = getnow()

    books_by_flavour: dict[str, list[Book]] = defaultdict(list)
    for book in title.books:
        if (
            book.location_kind == "prod"
            and not book.has_error
            and book.created_at <= (now - datetime.timedelta(days=30))
            and book.needs_file_operation is False
        ):
            books_by_flavour[book.flavour or ""].append(book)

    books_to_delete: list[Book] = []

    for _, books in books_by_flavour.items():
        # Group books by period (without the suffix)
        books_by_period: dict[str, list[Book]] = defaultdict(list)
        for book in books:
            if not book.date:
                continue
            books_by_period[book.date[:PERIOD_LENGTH]].append(book)

        # Keep last version from each of the 2 most recent periods
        sorted_periods = sorted(books_by_period.keys(), reverse=True)
        for period in sorted_periods[:2]:
            sorted_books_by_period = sort_books_by_filename_period(
                books_by_period[period]
            )
            # Mark all but the most recent one for deletion
            books_to_delete.extend(sorted_books_by_period[1:])

        # Mark the remainder of the books to be deleted.
        for period in sorted_periods[2:]:
            books_to_delete.extend(books_by_period[period])

    deletion_date = now + MillContext.old_book_deletion_delay

    for book in books_to_delete:
        logger.info(
            f"Marking book {book.id} for deletion, deletion_date={deletion_date}"
        )
        book.location_kind = "to_delete"
        book.deletion_date = deletion_date
        book.needs_file_operation = True
        book.events.append(
            f"{now}: marked for deletion due to retention policy, "
            f"will be deleted after {deletion_date}"
        )
        title.events.append(f"{now}: book {book.id} marked for deletion.")
        session.add(book)
        session.add(title)

    session.flush()


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

        # Determine if this book goes to staging or prod based on title maturity
        # For now, only 'robust' maturity move straight to prod, other maturity moves
        # through staging first
        goes_to_staging = title.maturity != "robust"

        target_locations = (
            [
                FileLocation(
                    MillContext.staging_warehouse_id,
                    MillContext.staging_base_path,
                    target_filename,
                )
            ]
            if goes_to_staging
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
        book.location_kind = "staging" if goes_to_staging else "prod"

        if not goes_to_staging:
            apply_retention_rules(session, title)

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while adding to title {title.id}\n{exc}"
        )
        title.events.append(
            f"{getnow()}: error encountered while adding book {book.id}\n{exc}"
        )
        book.has_error = True
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
        - Updates book needs_file_operation flag
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


def sort_books_by_filename_period(books: list[Book]) -> list[Book]:
    """Sort a list of books by period.

    Assumes:
    - the book's location exists since it contains the filename of the book
    """

    def sort_fn(book: Book) -> tuple[str, int, str]:
        period, suffix = get_period_and_suffix_from_filename(book.locations[0].filename)
        return (period, len(suffix), suffix)

    return sorted(
        books,
        key=sort_fn,
        reverse=True,
    )
