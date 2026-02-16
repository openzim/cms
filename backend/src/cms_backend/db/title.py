from pathlib import Path
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.book import (
    FileLocation,
    create_book_target_locations,
)
from cms_backend.db.collection import get_collection_by_name
from cms_backend.db.exceptions import RecordAlreadyExistsError, RecordDoesNotExistError
from cms_backend.db.models import CollectionTitle, Title
from cms_backend.schemas.orms import (
    BaseTitleCollectionSchema,
    ListResult,
    TitleLightSchema,
)
from cms_backend.utils.datetime import getnow


def get_title_by_id(session: OrmSession, *, title_id: UUID) -> Title:
    """Get a title by ID"""

    title = session.scalars(select(Title).where(Title.id == title_id)).one_or_none()
    if not title:
        raise RecordDoesNotExistError(f"Title with id {title_id} does not exist")
    return title


def get_title_by_name_or_none(session: OrmSession, *, name: str) -> Title | None:
    """Get a title by name if possible else None"""

    return session.scalars(select(Title).where(Title.name == name)).one_or_none()


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

    return title


def update_title(
    session: OrmSession,
    *,
    title_id: UUID,
    maturity: str | None,
    collection_titles: list[BaseTitleCollectionSchema] | None,
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

    return get_title_by_id(session, title_id=title.id)
