import datetime
from typing import Any, Literal
from uuid import UUID

import pycountry
from sqlalchemy import select, update
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db import count_from_stmt
from cms_backend.db.book_location import create_book_target_locations
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.flavour import get_title_flavours
from cms_backend.db.models import (
    Book,
    BookHistory,
    Title,
    ZimfarmNotification,
    ZimfarmRecipe,
)
from cms_backend.db.rules import (
    apply_retention_rules,
    has_flavour_mismatch,
    title_is_missing_mandatory_metadata,
)
from cms_backend.schemas.models import BookUpdateSchema, FileLocation
from cms_backend.schemas.orms import (
    BookFullSchema,
    BookHistorySchema,
    BookLocationSchema,
    ListResult,
)
from cms_backend.utils.datetime import getnow
from cms_backend.utils.zim import get_missing_metadata_keys


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
            is_backup=location.is_backup,
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
            is_backup=location.is_backup,
        )
        for location in book.locations
        if location.status == "target"
    ]

    if book.title:
        recipe_id = next(
            (
                title_flavour.recipe_id
                for title_flavour in book.title.flavours
                if title_flavour.flavour == book.flavour
            ),
            None,
        )
    else:
        recipe_id = None

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
        issues=book.issues,
        article_count=book.article_count,
        media_count=book.media_count,
        size=book.size,
        zimcheck_result_url=book.zimcheck_result_url,
        zim_metadata=book.zim_metadata,
        events=book.events,
        current_locations=current_locations,
        target_locations=target_locations,
        title_archived=book.title.archived if book.title else False,
        has_flavour_mismatch=has_flavour_mismatch(
            book.flavour, get_title_flavours(book.title)
        )
        if book.title
        else False,
        has_backup=any(
            current_location.is_backup for current_location in current_locations
        ),
        recipe_id=recipe_id,
    )


def create_book(
    session: OrmSession,
    *,
    book_id: UUID,
    author_id: UUID,
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

    create_book_history_entry(
        session, book, author_id, comment="Create initial history"
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
    session: OrmSession,
    *,
    book_id: UUID,
    force_delete: bool = False,
    deletion_delay: datetime.timedelta = Context.book_deletion_delay,
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

    deletion_date = now if force_delete else now + deletion_delay

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
    Book title must not be archived
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

    if book.title and book.title.archived:
        raise ValueError(f"Book title {book.title_id} is currently archived")

    if book.location_kind == destination:
        raise ValueError("Book destination must be different from current location.")

    current_location = next(
        (loc for loc in book.locations if loc.status == "current"), None
    )
    if not current_location:
        raise ValueError(f"Book {book_id} has no current location")

    if not book.title:
        raise ValueError(f"Book {book_id} has no associated title.")

    if destination == "prod":
        title_flavours = get_title_flavours(book.title)
        if has_flavour_mismatch(book.flavour, title_flavours):
            raise ValueError(
                f"Book flavour '{book.flavour}' is not in title expected flavours "
                f"{title_flavours}"
            )

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
) -> Literal["prod", "staging", "quarantine", "backup"]:
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

        if loc.warehouse_id == Context.staging_warehouse_id and loc.path.is_relative_to(
            Context.staging_base_path
        ):
            return "staging"

        if loc.warehouse_id == Context.backup_warehouse_id and loc.path.is_relative_to(
            Context.backup_base_path
        ):
            return "backup"

    return "prod"


def recover_book(session: OrmSession, book_id: UUID) -> Book:
    """Recover a book marked for deletion."""
    now = getnow()
    book = get_book_or_none(
        session,
        book_id,
        needs_processing=False,
        locations=["to_delete", "deleted"],
    )

    if book is None:
        raise RecordDoesNotExistError(f"Book {book_id} is not eligible for recovery.")

    if book.title and book.title.archived:
        raise ValueError(f"Book title {book.title_id} is currently archived")

    if book.location_kind == "deleted" and book.needs_file_operation is False:
        return _recover_deleted_book(session, book)

    if book.location_kind == "to_delete" and book.needs_file_operation is False:
        raise RecordDoesNotExistError(f"Book {book_id} is not eligible for recovery.")

    if book.deletion_date and book.deletion_date <= now:
        raise RecordDoesNotExistError(f"Book {book_id} is not eligible for recovery.")

    location_kind = determine_current_location_kind(book)
    book.needs_processing = False
    book.events.append(
        f"{now}: Book restored from {book.location_kind} to {location_kind}"
    )
    book.location_kind = location_kind
    book.deletion_date = None
    book.needs_file_operation = False
    update_book_issues(session, book)
    session.add(book)
    session.flush()
    return book


def get_differing_metadata_keys(book: Book) -> list[str]:
    """Get the list of metadata keys that are different between book and it's title.

    Assumes book and title both have mandatory metadata set.
    Assumes that the book name and title name already match, thus aren't checked.
    """

    if book.title is None:
        raise ValueError("Book has no associated title.")

    book_metadata = {
        "Title": book.zim_metadata["Title"],
        "Creator": book.zim_metadata["Creator"],
        "Publisher": book.zim_metadata["Publisher"],
        "Description": book.zim_metadata["Description"],
        "Language": book.zim_metadata["Language"],
        "Illustration_48x48@1": book.zim_metadata["Illustration_48x48@1"],
    }

    title_metadata = {
        "Title": book.title.title,
        "Creator": book.title.creator,
        "Publisher": book.title.publisher,
        "Description": book.title.description,
        "Language": book.title.language,
        "Illustration_48x48@1": book.title.illustration_48x48_at_1,
    }

    return [key for key in book_metadata if book_metadata[key] != title_metadata[key]]


def create_book_history_entry(
    session: OrmSession, book: Book, author_id: UUID, comment: str | None = None
) -> BookHistory:
    history_entry = BookHistory(
        name=book.name,
        comment=comment,
        flavour=book.flavour,
    )
    history_entry.book = book
    history_entry.author_id = author_id
    session.add(history_entry)
    return history_entry


def update_book(
    session: OrmSession, *, author_id: UUID, book_id: UUID, payload: BookUpdateSchema
) -> Book:
    book = get_book(session, book_id)
    if book.location_kind == "deleted":
        raise RecordDoesNotExistError(f"Book {book_id} is already deleted.")

    if book.title and book.title.archived:
        raise ValueError(f"Book title {book.title_id} is currently archived")

    # Return early if no update data
    update_data = payload.model_dump(
        exclude_unset=True, exclude={"comment"}, mode="json"
    )
    if not update_data:
        return book

    if payload.flavour and payload.flavour == book.flavour:
        return book

    book = session.scalars(
        update(Book).where(Book.id == book.id).values(**update_data).returning(Book)
    ).one()
    update_book_issues(session, book)

    create_book_history_entry(session, book, author_id, payload.comment)
    session.flush()
    return book


def create_book_history_schema(entry: BookHistory) -> BookHistorySchema:
    return BookHistorySchema(
        id=entry.id,
        created_at=entry.created_at,
        name=entry.name,
        flavour=entry.flavour,
        comment=entry.comment,
        author=entry.author.display_name,
    )


def get_book_history(
    session: OrmSession, *, book_id: UUID, skip: int, limit: int
) -> ListResult[BookHistorySchema]:
    """Get a book's history"""
    book = get_book(session, book_id)
    stmt = (
        select(BookHistory)
        .where(BookHistory.book_id == book.id)
        .options(selectinload(BookHistory.author))
        .order_by(BookHistory.created_at.desc())
    )
    return ListResult[BookHistorySchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_book_history_schema(entry)
            for entry in session.scalars(stmt.offset(skip).limit(limit)).all()
        ],
    )


def get_book_history_entry_or_none(
    session: OrmSession, *, book_id: UUID, history_id: UUID
) -> BookHistory | None:
    """Get a book's history entry or None if it does not exist"""
    book = get_book(session, book_id)
    return session.scalars(
        select(BookHistory).where(
            BookHistory.id == history_id, BookHistory.book_id == book.id
        )
    ).one_or_none()


def get_book_history_entry(
    session: OrmSession, *, book_id: UUID, history_id: UUID
) -> BookHistory:
    """Get a book's history entry"""
    if history_entry := get_book_history_entry_or_none(
        session, book_id=book_id, history_id=history_id
    ):
        return history_entry
    raise RecordDoesNotExistError(
        f"Book '{book_id}' does not have a history entry with id {history_id}"
    )


def revert_book(
    session: OrmSession,
    *,
    book_id: UUID,
    history_id: UUID,
    author_id: UUID,
    comment: str | None = None,
) -> Book:
    """Revert the book configuration and settings to those defined in history_id"""
    entry = get_book_history_entry(session, book_id=book_id, history_id=history_id)
    book = update_book(
        session,
        author_id=author_id,
        book_id=book_id,
        payload=BookUpdateSchema(
            comment=comment,
            flavour=entry.flavour,
        ),
    )

    return book


def update_book_issues(session: OrmSession, book: Book, *, update_events: bool = False):
    """
    Update book issues based on it's associated title and optionally update book events.

    A book's issues will not be updated if:
    - it has no associated title
    - it is missing mandatory metadata keys
    - it's associated title is missing mandatory metadata
    - it's location kind is to_delete or deleted
    """
    if (
        not book.title
        or get_missing_metadata_keys(book.zim_metadata)
        or title_is_missing_mandatory_metadata(book.title)
        or book.location_kind in ["deleted", "to_delete"]
    ):
        return

    issues: list[str] = []

    unknown_languages: list[str] = []
    for language_code in book.zim_metadata["Language"].split(","):
        if pycountry.languages.get(alpha_3=language_code) is None:  # pyright: ignore[reportUnknownMemberType]
            unknown_languages.append(language_code)

    if unknown_languages:
        issues.append("invalid language code")
        if update_events:
            book.events.append(
                f"{getnow()}: book has unknown language code(s) {unknown_languages}"
            )

    different_metadata_keys = get_differing_metadata_keys(book)
    if different_metadata_keys:
        issues.append("metadata mismatch")
        if update_events:
            book.events.append(
                f"{getnow()}: book metadata is different from title metadata: "
                f"{','.join(different_metadata_keys)}"
            )

    if has_flavour_mismatch(book.flavour, get_title_flavours(book.title)):
        issues.append("flavour mismatch")
        if update_events:
            book.events.append(
                f"{getnow()}: book flavour is not in list of title flavours"
            )

    # Get the latest prod book that isn't the current book
    latest_book = session.scalars(
        select(Book)
        .where(
            Book.location_kind == "prod",
            Book.id != book.id,
            Book.title_id == book.title_id,
            Book.flavour == book.flavour,
        )
        .order_by(Book.created_at.desc())
    ).first()
    if latest_book is None:
        latest_book = book

    collection_media_count_change_threshold = min(
        [
            Context.media_count_change_threshold
            if tc.collection.media_count_change_threshold is None
            else tc.collection.media_count_change_threshold
            for tc in book.title.collections
        ],
        default=Context.media_count_change_threshold,
    )
    collection_article_count_change_threshold = min(
        [
            Context.article_count_change_threshold
            if tc.collection.article_count_change_threshold is None
            else tc.collection.article_count_change_threshold
            for tc in book.title.collections
        ],
        default=Context.article_count_change_threshold,
    )

    media_count_diff = (
        abs(book.media_count - latest_book.media_count)
    ) / latest_book.media_count

    if media_count_diff > collection_media_count_change_threshold:
        issues.append("media count")
        book.events.append(
            f"{getnow()}: book media count exceeds collection median threshold by "
            f"{media_count_diff * 100}%"
        )

    article_count_diff = (
        abs(book.article_count - latest_book.article_count)
    ) / latest_book.article_count
    if article_count_diff > collection_article_count_change_threshold:
        issues.append("article count")
        book.events.append(
            f"{getnow()}: book article count exceeds collection median threshold by "
            f"{article_count_diff * 100}%"
        )
    book.issues = issues
    session.add(book)
    session.flush()


def backup_book(
    session: OrmSession,
    *,
    book_id: UUID,
) -> Book:
    """Create a backup of a book."""
    book = get_book_or_none(
        session,
        book_id=book_id,
        has_error=False,
        needs_processing=False,
        needs_file_operation=False,
        locations=["staging", "quarantine", "prod"],
    )

    if book is None:
        raise RecordDoesNotExistError(
            f"Book {book_id} does not meet criteria to be backed up."
        )

    if book.title is None:
        raise ValueError("Book has no associated title.")

    if book.title.archived:
        raise ValueError(f"Book title {book.title_id} is currently archived")

    current_location = next(
        (loc for loc in book.locations if loc.status == "current"), None
    )

    if not current_location:
        raise ValueError(f"Book {book_id} has no current location")

    existing_backup = next(
        (loc for loc in book.locations if loc.status == "current" and loc.is_backup),
        None,
    )

    if existing_backup:
        raise ValueError("Book already has a backup.")

    target_locations = [
        FileLocation(loc.warehouse_id, loc.path, loc.filename)
        for loc in book.locations
        if loc.status == "current"
    ]
    target_locations.append(
        FileLocation(
            Context.backup_warehouse_id,
            Context.backup_base_path,
            current_location.filename,
            is_backup=True,
        )
    )
    create_book_target_locations(
        session=session,
        book=book,
        target_locations=target_locations,
    )
    book.events.append(
        f"{getnow()}: Book scheduled to be copied from '{book.location_kind}' to "
        f"'backup'"
    )

    session.add(book)
    session.flush()
    return book


def remove_book_backup(
    session: OrmSession,
    *,
    book_id: UUID,
) -> Book:
    """Create a backup of a book."""
    book = get_book_or_none(
        session,
        book_id=book_id,
        has_error=False,
        needs_processing=False,
        needs_file_operation=False,
        locations=["staging", "quarantine", "prod", "deleted"],
    )

    if book is None:
        raise RecordDoesNotExistError(
            f"Book {book_id} does not meet criteria for it's backup to be removed."
        )

    if book.title is None:
        raise ValueError("Book has no associated title.")

    if book.title.archived:
        raise ValueError(f"Book title {book.title_id} is currently archived")

    existing_backups = [
        loc for loc in book.locations if loc.status == "current" and loc.is_backup
    ]
    if not existing_backups:
        raise ValueError("Book does not have a backup.")

    target_locations = [
        FileLocation(loc.warehouse_id, loc.path, loc.filename)
        for loc in book.locations
        if loc.status == "current" and not loc.is_backup
    ]

    for backup in existing_backups:
        backup.is_backup = False
        session.add(backup)

    if book.location_kind == "deleted":
        # book has no target locations and only backups exist
        book.location_kind = "to_delete"
        book.needs_file_operation = True
        book.deletion_date = getnow()
        session.add(book)
        session.flush()
        return book

    create_book_target_locations(
        session=session,
        book=book,
        target_locations=target_locations,
    )

    book.events.append(f"{getnow()}: Book backup scheduled to be removed")
    session.add(book)
    session.flush()
    return book


def book_goes_to_staging(book: Book) -> bool:
    """Determine if a book goes to staging.

    A book goes to `prod` if:
    - it has a title
    - book title maturity is 'stable', and
    - book has no issues
    """
    if not book.title:
        return True
    return book.title.maturity != "stable" or len(book.issues) != 0


def process_book(
    session: OrmSession,
    book: Book,
    *,
    update_events: bool = False,
) -> Book:
    """Process a book as if it just arrived.

    - Makes the same assumptions as the update_book_issues function
    - Books with location kind in "to_delete" and "deleted" are skipped
    """
    if book.location_kind in ["to_delete", "deleted"]:
        logger.debug(
            f"Skipping action to process book {book.id} with location kind "
            f"{book.location_kind}"
        )
        return book

    if book.needs_processing or book.needs_file_operation:
        raise ValueError(
            f"Cannot process book {book.id} belonging to title "
            f"'{book.title.name}' because book either needs "  # pyright: ignore[reportOptionalMemberAccess]
            "processing or file operation."
        )

    if not book.filename:
        raise ValueError(f"Book {book.id} has no filename")

    current_location = next(
        (
            loc
            for loc in book.locations
            if loc.status == "current" and not loc.is_backup
        ),
        None,
    )
    if not current_location:
        logger.debug(
            f"Skipping action to process book {book.id} because it has no current "
            "location"
        )
        return book

    update_book_issues(session, book, update_events=update_events)
    goes_to_staging = book_goes_to_staging(book)
    book.location_kind = "staging" if goes_to_staging else "prod"
    target_locations = (
        [
            FileLocation(
                Context.staging_warehouse_id,
                Context.staging_base_path,
                book.filename,
            )
        ]
        if goes_to_staging
        else [
            FileLocation(tc.collection.warehouse_id, tc.path, book.filename)
            for tc in book.title.collections  # pyright: ignore[reportOptionalMemberAccess]
        ]
    )
    create_book_target_locations(
        session=session,
        book=book,
        target_locations=target_locations,
    )
    return book


def _recover_deleted_book(session: OrmSession, book: Book) -> Book:
    """Helper function to recover a book that is deleted.

    This can only happen if the book has a backup.
    """
    if book.title is None:
        raise ValueError("Book has no associated title.")

    existing_backup = next(
        (loc for loc in book.locations if loc.status == "current" and loc.is_backup),
        None,
    )

    if not existing_backup:
        raise ValueError("Book does not have a backup.")

    target_filename = existing_backup.filename
    # update the book location so we can update book issues
    book.location_kind = "staging"
    update_book_issues(session, book)
    goes_to_staging = book_goes_to_staging(book)
    # reset book location based on issues and title maturity
    book.location_kind = "staging" if goes_to_staging else "prod"
    book.deletion_date = None

    target_locations = (
        [
            FileLocation(
                Context.staging_warehouse_id,
                Context.staging_base_path,
                target_filename,
            )
        ]
        if goes_to_staging
        else [
            FileLocation(tc.collection.warehouse_id, tc.path, target_filename)
            for tc in book.title.collections
        ]
    )
    # move_files does not consider backup locations as sources as it removes excessive
    # current locations. so, we need to remove the backup property and recreate a new
    # backup in target. This duplication will be a no-op that will only update the
    # is_backup property of the existing backup.
    existing_backup.is_backup = False
    target_locations.append(
        FileLocation(
            existing_backup.warehouse_id,
            existing_backup.path,
            target_filename,
            is_backup=True,
        )
    )

    create_book_target_locations(
        session=session,
        book=book,
        target_locations=target_locations,
    )
    book.events.append(f"{getnow()}: Book restored from 'deleted'")
    session.add(book)
    session.flush()

    return book


def book_has_recipe_issue(
    book_flavour: str | None, book_title: Title, recipe: ZimfarmRecipe
) -> bool:
    """Check if book has recipe issues."""
    if recipe.title_id is None:
        return True
    if recipe.title_id != book_title.id and book_title.id not in [
        tf.recipe_id for tf in book_title.flavours
    ]:
        return True
    if has_flavour_mismatch(book_flavour, [tf.flavour for tf in recipe.flavours]):
        return True
    return False
