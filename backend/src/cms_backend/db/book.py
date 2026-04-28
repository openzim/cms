from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.context import Context
from cms_backend.db.book_location import create_book_target_locations
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Book, ZimfarmNotification
from cms_backend.db.title import apply_retention_rules
from cms_backend.schemas.models import FileLocation
from cms_backend.schemas.orms import BookFullSchema, BookLocationSchema
from cms_backend.utils.datetime import getnow


def get_book_or_none(
    session: OrmSession,
    book_id: UUID,
    *,
    needs_file_operation: bool | None = None,
    needs_processing: bool | None = None,
    locations: list[str] | None = None,
    has_error: bool | None = None,
) -> Book | None:
    """Get a book by ID if possible else None"""
    return session.scalars(
        select(Book)
        .where(
            # If a client provides an argument i.e it is not None,
            # we compare the corresponding model field against the argument,
            # otherwise, we compare the argument to its default which translates
            # to a SQL true i.e we don't filter based on this argument (a no-op).
            (Book.id == book_id),
            (Book.needs_file_operation.is_(needs_file_operation))
            | (needs_file_operation is None),
            (Book.needs_processing.is_(needs_processing)) | (needs_processing is None),
            (Book.has_error.is_(has_error)) | (has_error is None),
            (Book.location_kind.in_(locations or [])) | (locations is None),
        )
        .options(
            selectinload(Book.title),
            selectinload(Book.zimfarm_notification),
            selectinload(Book.locations),
        )
    ).one_or_none()


def get_book(session: OrmSession, book_id: UUID) -> Book:
    """Get a book by ID if possible else raise an exception"""
    if (book := get_book_or_none(session, book_id=book_id)) is None:
        raise RecordDoesNotExistError(f"Book with ID {book_id} does not exist")
    return book


def create_book_full_schema(book: Book) -> BookFullSchema:
    # Separate current and target locations
    current_locations = [
        BookLocationSchema(
            warehouse_name=location.warehouse.name,
            path=str(location.path),
            filename=location.filename,
            status=location.status,
        )
        for location in book.locations
        if location.status == "current"
    ]

    target_locations = [
        BookLocationSchema(
            warehouse_name=location.warehouse.name,
            path=str(location.path),
            filename=location.filename,
            status=location.status,
        )
        for location in book.locations
        if location.status == "target"
    ]

    return BookFullSchema(
        id=book.id,
        title_id=book.title_id,
        needs_processing=book.needs_processing,
        has_error=book.has_error,
        needs_file_operation=book.needs_file_operation,
        location_kind=book.location_kind,
        created_at=book.created_at,
        name=book.name,
        date=book.date,
        deletion_date=book.deletion_date,
        flavour=book.flavour,
        article_count=book.article_count,
        media_count=book.media_count,
        size=book.size,
        zimcheck_result_url=book.zimcheck_result_url,
        zim_metadata=book.zim_metadata,
        events=book.events,
        current_locations=current_locations,
        target_locations=target_locations,
    )


def create_book(
    session: OrmSession,
    *,
    book_id: UUID,
    article_count: int,
    media_count: int,
    size: int,
    zim_metadata: dict[str, Any],
    zimcheck_result_url: str,
    zimfarm_notification: ZimfarmNotification,
) -> Book:
    """Create a new book"""

    # Extract metadata fields (optional fields may not be present)
    name = zim_metadata.get("Name")
    date = zim_metadata.get("Date")
    flavour = zim_metadata.get("Flavour") or None

    book = Book(
        id=book_id,
        created_at=getnow(),
        article_count=article_count,
        media_count=media_count,
        size=size,
        zim_metadata=zim_metadata,
        zimcheck_result_url=zimcheck_result_url,
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


def delete_book(
    session: OrmSession, *, book_id: UUID, force_delete: bool = False
) -> Book:
    """Mark a book as deleted.

    - Only books in staging, prod or quarantine are eligible to be marked for deletion.
    - Setting force_delete makes the book deletion_date to be set to now instead of the
       env BOOK_DELETION_DELAY. This potentially makes the book unrecoverable.
    """
    now = getnow()
    book = get_book_or_none(
        session,
        book_id=book_id,
        needs_processing=False,
        needs_file_operation=False,
        locations=["staging", "prod", "quarantine"],
    )
    if book is None:
        raise RecordDoesNotExistError(
            f"Book {book_id} does not meet criteria to be marked as deleted."
        )

    deletion_date = now if force_delete else now + Context.book_deletion_delay

    if book.location_kind in ("staging", "prod", "quarantine"):
        book.deletion_date = deletion_date
    else:  # should never get here because of filtering by locations
        raise ValueError(
            "Cannot determine how to delete book with location kind "
            f"'{book.location_kind}'"
        )
    book.location_kind = "to_delete"
    book.needs_file_operation = True
    book.events.append(
        f"{now}: marked for deletion, will be deleted after {deletion_date}"
    )
    session.add(book)
    session.flush()
    return book


def move_book(
    session: OrmSession, *, book_id: UUID, destination: Literal["staging", "prod"]
) -> Book:
    """Move a book in staging/prod to prod/staging.

    Destination location must be different from current location.
    """
    book = get_book_or_none(
        session,
        book_id=book_id,
        needs_file_operation=False,
        needs_processing=False,
        locations=["staging", "prod"],
        has_error=False,
    )

    if book is None:
        raise RecordDoesNotExistError(
            f"Book {book_id} does not meet criteria to be moved."
        )

    if book.location_kind == destination:
        raise ValueError("Book destination must be different from current location.")

    current_location = next(
        (loc for loc in book.locations if loc.status == "current"), None
    )
    if not current_location:
        raise ValueError(f"Book {book_id} has no current location")

    if not book.title:
        raise ValueError(f"Book {book_id} has no associated title.")

    existing_filename = current_location.filename

    goes_to_staging = destination == "staging"
    target_locations = (
        [
            FileLocation(
                Context.staging_warehouse_id,
                Context.staging_base_path,
                existing_filename,
            )
        ]
        if goes_to_staging
        else [
            FileLocation(tc.collection.warehouse_id, tc.path, existing_filename)
            for tc in book.title.collections
        ]
    )

    create_book_target_locations(
        session=session,
        book=book,
        target_locations=target_locations,
    )
    book.events.append(
        f"{getnow()}: Book scheduled to be moved from '{book.location_kind}' to "
        f"'{destination}'"
    )
    book.location_kind = "staging" if goes_to_staging else "prod"
    session.add(book)
    session.flush()

    if not goes_to_staging:
        apply_retention_rules(session, book.title)

    return book


def determine_current_location_kind(
    book: Book,
) -> Literal["prod", "staging", "quarantine"]:
    """Determine the location kind of a book based on its current locations."""
    current_locations = [loc for loc in book.locations if loc.status == "current"]
    if not current_locations:
        raise ValueError(f"Book {book.id} has no current location.")

    for loc in current_locations:
        if (
            loc.warehouse_id == Context.quarantine_warehouse_id
            and loc.path.is_relative_to(Context.quarantine_base_path)
        ):
            return "quarantine"

        if (
            loc.warehouse_id == Context.staging_warehouse_id
            and loc.path.is_relative_to(Context.staging_base_path)
        ):
            return "staging"

    return "prod"


def recover_book(session: OrmSession, book_id: UUID) -> Book:
    """Recover a book marked for deletion."""
    now = getnow()
    book = get_book_or_none(
        session,
        book_id,
        needs_file_operation=True,
        needs_processing=False,
        locations=["to_delete"],
    )
    if book is None or (book.deletion_date and book.deletion_date <= now):
        raise RecordDoesNotExistError(f"Book {book_id} is not eligible for recovery.")

    location_kind = determine_current_location_kind(book)
    book.needs_processing = False
    book.events.append(
        f"{now}: Book restored from {book.location_kind} to {location_kind}"
    )
    book.location_kind = location_kind
    book.deletion_date = None
    book.needs_file_operation = False
    session.add(book)
    session.flush()
    return book
