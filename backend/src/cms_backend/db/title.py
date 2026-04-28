import datetime
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import Date, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db import count_from_stmt
from cms_backend.db.book_location import create_book_target_locations
from cms_backend.db.collection import get_collection_by_name
from cms_backend.db.event import create_title_modified_event
from cms_backend.db.exceptions import RecordAlreadyExistsError, RecordDoesNotExistError
from cms_backend.db.models import (
    Book,
    CollectionTitle,
    Title,
)
from cms_backend.schemas.models import FileLocation
from cms_backend.schemas.orms import (
    BaseTitleCollectionSchema,
    BookLightSchema,
    ListResult,
    TitleCollectionSchema,
    TitleFullSchema,
    TitleLightSchema,
)
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import (
    PERIOD_LENGTH,
    get_period_and_suffix_from_filename,
)


def create_title_full_schema(title: Title) -> TitleFullSchema:
    """Create a schema of a tilte."""
    return TitleFullSchema(
        id=title.id,
        name=title.name,
        maturity=title.maturity,
        events=title.events,
        books=[
            BookLightSchema(
                id=book.id,
                title_id=book.title_id,
                needs_processing=book.needs_processing,
                has_error=book.has_error,
                needs_file_operation=book.needs_file_operation,
                location_kind=book.location_kind,
                created_at=book.created_at,
                deletion_date=book.deletion_date,
                name=book.name,
                date=book.date,
                flavour=book.flavour,
            )
            for book in sorted(
                title.books,
                key=lambda book: (
                    (
                        datetime.date.fromisoformat(book.date)
                        if book.date
                        else datetime.datetime.fromtimestamp(0).date()
                    ),
                    book.created_at,
                ),
                reverse=True,
            )
        ],
        collections=[
            TitleCollectionSchema(
                collection_id=tc.collection_id,
                collection_name=tc.collection.name,
                path=str(tc.path),
            )
            for tc in title.collections
        ],
    )


def get_title_by_id_or_none(session: OrmSession, *, title_id: UUID) -> Title | None:
    """Get a title by ID"""
    return session.scalars(
        select(Title).options(selectinload(Title.books)).where(Title.id == title_id)
    ).one_or_none()


def get_title_by_id(session: OrmSession, *, title_id: UUID) -> Title:
    """Get a title by ID"""

    title = get_title_by_id_or_none(session, title_id=title_id)
    if not title:
        raise RecordDoesNotExistError(f"Title with id {title_id} does not exist")
    return title


def get_title_by_name_or_none(session: OrmSession, *, name: str) -> Title | None:
    """Get a title by name if possible else None"""

    return session.scalars(
        select(Title).options(selectinload(Title.books)).where(Title.name == name)
    ).one_or_none()


def get_title_by_name(session: OrmSession, *, name: str) -> Title:
    """Get a title or raise RecordDoesNotExistError if it doesn't exist."""
    if (title := get_title_by_name_or_none(session, name=name)) is None:
        raise RecordDoesNotExistError(f"Title with name '{name}' does not exist")
    return title


def get_titles(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    name: str | None = None,
    omit_names: list[str] | None = None,
) -> ListResult[TitleLightSchema]:
    """Get a list of titles"""

    stmt = (
        select(
            Title.id.label("title_id"),
            Title.name.label("title_name"),
            Title.maturity.label("title_maturity"),
        )
        .order_by(Title.name)
        .where(
            # If a client provides an argument i.e it is not None,
            # we compare the corresponding model field against the argument,
            # otherwise, we compare the argument to its default which translates
            # to a SQL true i.e we don't filter based on this argument (a no-op).
            (
                Title.name.ilike(f"%{name if name is not None else ''}%")
                | (name is None)
            ),
            (Title.name.not_in(omit_names or []) | (omit_names is None)),
        )
    )

    return ListResult[TitleLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            TitleLightSchema(
                id=title_id,
                name=title_name,
                maturity=title_maturity,
            )
            for (
                title_id,
                title_name,
                title_maturity,
            ) in session.execute(stmt.offset(skip).limit(limit)).all()
        ],
    )


def create_title(
    session: OrmSession,
    *,
    name: str,
    maturity: str | None,
    collection_titles: list[BaseTitleCollectionSchema] | None,
) -> Title:
    """Create a new title"""

    title = Title(
        name=name,
    )
    if maturity:
        title.maturity = maturity
    title.events.append(f"{getnow()}: title created")

    session.add(title)

    if collection_titles:
        # Create the collection titles for the title
        for entry in collection_titles:
            collection = get_collection_by_name(
                session, collection_name=entry.collection_name
            )

            collection_title = CollectionTitle(path=Path(entry.path))
            collection_title.collection = collection
            collection_title.title = title

            session.add(collection_title)

    try:
        session.flush()
    except IntegrityError as exc:
        if isinstance(exc.orig, UniqueViolation):
            raise RecordAlreadyExistsError(
                f"Title with name {name} already exists"
            ) from exc
        logger.exception("Unknown exception encountered while creating title")
        raise

    create_title_modified_event(
        session, action="created", title_name=title.name, title_id=title.id
    )

    return title


def update_title(
    session: OrmSession,
    *,
    title_id: UUID,
    maturity: str | None = None,
    name: str | None = None,
    collection_titles: list[BaseTitleCollectionSchema] | None = None,
) -> Title:
    """Update a title's maturity and/or collection_titles.

    When collection_titles changes:
    - Finds all books associated with this title where location_kind == 'prod'
    - Updates their locations according to the new collection configuration
    - Sets the needs_file_operation flag to true for these books
    """
    title = get_title_by_id(session, title_id=title_id)

    # Update maturity if provided
    if maturity is not None and maturity != title.maturity:
        old_maturity = title.maturity
        title.maturity = maturity
        title.events.append(
            f"{getnow()}: maturity updated from {old_maturity} to {maturity}"
        )

    name_changed: bool = False
    # Update name if provided
    if name and name != title.name:
        old_name = title.name
        title.name = name
        title.events.append(f"{getnow()}: name updated from {old_name} to {name}")
        name_changed = True
        session.add(title)
        try:
            session.flush()
        except IntegrityError as exc:
            raise RecordAlreadyExistsError(
                f"Title with name '{name}' already exists"
            ) from exc

    # Determine if collection titles changed
    collection_titles_changed = False

    if collection_titles is not None:
        if len(title.collections) != len(collection_titles):
            collection_titles_changed = True
        else:
            current_collections: set[str] = {
                f"{tc.collection.name}:{tc.path}" for tc in title.collections
            }
            new_collections: set[str] = {
                f"{entry.collection_name}:{entry.path}" for entry in collection_titles
            }

            if current_collections != new_collections:
                collection_titles_changed = True

        if collection_titles_changed:
            # Remove existing collection_titles
            for tc in title.collections:
                session.delete(tc)

            for entry in collection_titles:
                collection = get_collection_by_name(
                    session, collection_name=entry.collection_name
                )

                collection_title = CollectionTitle(path=Path(entry.path))
                collection_title.collection = collection
                collection_title.title = title

                session.add(collection_title)

            title.events.append(f"{getnow()}: collection titles updated")

    # If collection_titles changed, update book locations for prod books
    if collection_titles_changed:
        prod_books = [book for book in title.books if book.location_kind == "prod"]
        for book in prod_books:
            # Since book is already in prod, it should have at least one
            # current location
            if not book.locations:
                raise ValueError(
                    f"Book {book.id} has location_kind='prod' but no locations"
                )

            current_location = next(
                (loc for loc in book.locations if loc.status == "current"),
                None,
            )
            if not current_location:
                raise ValueError(
                    f"Book {book.id} has location_kind='prod' but no current location"
                )

            # Build new target locations based on updated collection_titles
            target_locations = [
                FileLocation(
                    tc.collection.warehouse_id, tc.path, current_location.filename
                )
                for tc in title.collections
            ]

            for loc in list(book.locations):
                if loc.status == "target":
                    session.delete(loc)

            create_book_target_locations(
                session=session,
                book=book,
                target_locations=target_locations,
            )

            book.events.append(
                f"{getnow()}: locations updated due to title collection change"
            )

    if name_changed:
        create_title_modified_event(
            session, action="updated", title_name=title.name, title_id=title.id
        )
    return get_title_by_id(session, title_id=title.id)


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
    for book in session.scalars(
        select(Book).where(
            Book.title_id == title.id,
            Book.has_error.is_(False),
            Book.date.is_not(None),
            sql_cast(Book.date, Date) <= (now - datetime.timedelta(days=30)).date(),
            Book.location_kind == "prod",
            Book.needs_file_operation.is_(False),
        )
    ).all():
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

    deletion_date = now + Context.book_deletion_delay

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
