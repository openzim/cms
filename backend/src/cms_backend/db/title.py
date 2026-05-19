import datetime
from pathlib import Path
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.book import delete_book, recover_book
from cms_backend.db.book_location import create_book_target_locations
from cms_backend.db.collection import get_collection_by_name
from cms_backend.db.event import create_title_modified_event
from cms_backend.db.exceptions import RecordAlreadyExistsError, RecordDoesNotExistError
from cms_backend.db.models import (
    Collection,
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
from cms_backend.utils import is_valid_uuid
from cms_backend.utils.datetime import getnow


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
        archived=title.archived,
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


def get_title_or_none(session: OrmSession, title_identifier: str) -> Title | None:
    if is_valid_uuid(title_identifier):
        return get_title_by_id_or_none(session, title_id=UUID(title_identifier))
    else:
        return get_title_by_name_or_none(session, name=title_identifier)


def get_title(session: OrmSession, title_identifier: str) -> Title:
    if is_valid_uuid(title_identifier):
        return get_title_by_id(session, title_id=UUID(title_identifier))
    else:
        return get_title_by_name(session, name=title_identifier)


def get_titles(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    name: str | None = None,
    omit_names: list[str] | None = None,
    collection_name: str | None = None,
    archived: bool = False,
) -> ListResult[TitleLightSchema]:
    """Get a list of titles"""

    stmt = (
        select(
            Title.id.label("title_id"),
            Title.name.label("title_name"),
            Title.maturity.label("title_maturity"),
            Title.archived.label("title_archived"),
        )
        .join(CollectionTitle, CollectionTitle.title_id == Title.id, isouter=True)
        .join(Collection, CollectionTitle.collection_id == Collection.id, isouter=True)
        .distinct()
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
            (Title.archived.is_(archived)),
            (
                Collection.name.ilike(
                    f"%{collection_name if collection_name is not None else ''}%"
                )
                | (collection_name is None)
            ),
        )
    )

    return ListResult[TitleLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            TitleLightSchema(
                id=title_id,
                name=title_name,
                maturity=title_maturity,
                archived=title_archived,
            )
            for (
                title_id,
                title_name,
                title_maturity,
                title_archived,
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
    if title.archived:
        raise RecordDoesNotExistError("Title is archived")

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

            title.collections.clear()

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


def archive_title(
    session: OrmSession,
    title_identifier: str,
) -> Title:
    """Mark a title as archived.

    All books belonging to the title are marked for deletion immediately
    """
    title = get_title(session, title_identifier=title_identifier)
    if title.archived:
        raise RecordDoesNotExistError("Title is archived.")

    title.archived = True
    now = getnow()
    title.events.append(f"{now}: marked title as archived.")
    logger.info(f"marking books belonging to title {title.id} for deletion.")

    nb_deleted = 0
    for book in title.books:
        with session.begin_nested():
            try:
                delete_book(session, book_id=book.id)
            except Exception:
                logger.exception(f"error while deleting book {book.id}")
            else:
                nb_deleted += 1

    if nb_deleted:
        title.events.append(f"{now}: marked books in title for deletion.")

    session.add(title)
    session.flush()

    return title


def archive_titles(
    session: OrmSession,
    *,
    title_names: list[str],
) -> None:
    """Archive a list of titles"""
    for title_name in title_names:
        archive_title(session, title_name)


def restore_title(
    session: OrmSession,
    title_identifier: str,
) -> Title:
    """Remove a title from the archive status.

    Restores books belonging to title that have not been deleted.
    """

    title = get_title(session, title_identifier=title_identifier)
    if not title.archived:
        raise RecordDoesNotExistError("Title is not archived.")

    title.archived = False
    now = getnow()
    title.events.append(f"{now}: restored title from archive")
    logger.info(
        f"recovering books belonging to title {title.id} that have been marked for "
        "deletion."
    )
    nb_recovered = 0
    for book in title.books:
        with session.begin_nested():
            try:
                recover_book(session, book.id)
            except Exception:
                logger.exception(f"error while restoring title book {book.id}")
            else:
                nb_recovered += 1

    if nb_recovered:
        title.events.append(f"{now}: recovered books in title for deletion.")

    session.add(title)
    session.flush()

    return title


def restore_titles(
    session: OrmSession,
    *,
    title_names: list[str],
) -> None:
    """Restore a list of archived titles"""
    for title_name in title_names:
        restore_title(session, title_name)
