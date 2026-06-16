import datetime
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.book import (
    delete_book,
    process_book,
    recover_book,
    update_book_issues,
)
from cms_backend.db.book_location import create_book_target_locations
from cms_backend.db.collection import get_collection_by_name
from cms_backend.db.event import create_title_modified_event
from cms_backend.db.exceptions import RecordAlreadyExistsError, RecordDoesNotExistError
from cms_backend.db.flavour import get_title_flavours
from cms_backend.db.models import (
    Collection,
    CollectionTitle,
    Title,
    TitleFlavour,
    TitleHistory,
)
from cms_backend.db.rules import apply_retention_rules, has_flavour_mismatch
from cms_backend.schemas.models import (
    FileLocation,
    TitleCreateSchema,
    TitleUpdateSchema,
)
from cms_backend.schemas.orms import (
    BaseTitleCollectionSchema,
    BookLightSchema,
    ListResult,
    TitleCollectionSchema,
    TitleFullSchema,
    TitleHistorySchema,
    TitleLightSchema,
)
from cms_backend.utils import is_valid_uuid
from cms_backend.utils.datetime import getnow


def create_title_full_schema(title: Title) -> TitleFullSchema:
    """Create a full schema of a title."""
    title_flavours = get_title_flavours(title)
    return TitleFullSchema(
        id=title.id,
        name=title.name,
        maturity=title.maturity,
        events=title.events,
        title=title.title,
        creator=title.creator,
        publisher=title.publisher,
        description=title.description,
        language=title.language,
        illustration_48x48_at_1=title.illustration_48x48_at_1,
        long_description=title.long_description,
        license=title.license,
        relation=title.relation,
        source=title.source,
        flavours=title_flavours,
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
                issues=book.issues,
                has_flavour_mismatch=has_flavour_mismatch(book.flavour, title_flavours),
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


def create_title_light_schema(title: Title) -> TitleLightSchema:
    """Create a light schema of a title."""
    return TitleLightSchema(
        id=title.id,
        name=title.name,
        maturity=title.maturity,
        archived=title.archived,
        title=title.title,
        creator=title.creator,
        publisher=title.publisher,
        description=title.description,
        language=title.language,
        illustration_48x48_at_1=title.illustration_48x48_at_1,
        long_description=title.long_description,
        license=title.license,
        relation=title.relation,
        source=title.source,
    )


def get_title_by_id_or_none(session: OrmSession, *, title_id: UUID) -> Title | None:
    """Get a title by ID"""
    return session.scalars(
        select(Title)
        .options(
            selectinload(Title.books),
            selectinload(Title.collections),
            selectinload(Title.zimfarm_recipes),
            selectinload(Title.flavours),
        )
        .where(Title.id == title_id)
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
        select(Title)
        .options(
            selectinload(Title.books),
            selectinload(Title.collections),
            selectinload(Title.zimfarm_recipes),
            selectinload(Title.flavours),
        )
        .where(Title.name == name)
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
            Title.title.label("title_title"),
            Title.creator.label("title_creator"),
            Title.publisher.label("title_publisher"),
            Title.description.label("title_description"),
            Title.language.label("title_language"),
            Title.illustration_48x48_at_1.label("title_illustration_48x48_at_1"),
            Title.long_description.label("title_long_description"),
            Title.license.label("title_license"),
            Title.relation.label("title_relation"),
            Title.source.label("title_source"),
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
                title=title_title,
                creator=title_creator,
                publisher=title_publisher,
                description=title_description,
                language=title_language,
                illustration_48x48_at_1=title_illustration_48x48_at_1,
                long_description=title_long_description,
                license=title_license,
                relation=title_relation,
                source=title_source,
            )
            for (
                title_id,
                title_name,
                title_maturity,
                title_archived,
                title_title,
                title_creator,
                title_publisher,
                title_description,
                title_language,
                title_illustration_48x48_at_1,
                title_long_description,
                title_license,
                title_relation,
                title_source,
            ) in session.execute(stmt.offset(skip).limit(limit)).all()
        ],
    )


def create_title(
    session: OrmSession,
    *,
    author_id: UUID,
    payload: TitleCreateSchema,
    create_event: bool = True,
) -> Title:
    """Create a new title"""

    title = Title(
        name=payload.name,
    )
    if payload.maturity:
        title.maturity = payload.maturity
    title.title = payload.title
    title.creator = payload.creator
    title.publisher = payload.publisher
    title.language = payload.language
    title.illustration_48x48_at_1 = payload.illustration_48x48_at_1
    title.license = payload.license
    title.relation = payload.relation
    title.source = payload.source
    title.description = payload.description
    title.long_description = payload.long_description
    title.events.append(f"{getnow()}: title created")

    if payload.collection_titles:
        # Create the collection titles for the title
        for entry in payload.collection_titles:
            collection = get_collection_by_name(
                session, collection_name=entry.collection_name
            )

            collection_title = CollectionTitle(path=Path(entry.path))
            collection_title.collection = collection
            collection_title.title = title

            session.add(collection_title)

    if payload.flavours:
        for flavour in payload.flavours:
            title_flavour = TitleFlavour(flavour=flavour)
            title.flavours.append(title_flavour)

    create_title_history_entry(
        session, title, author_id, comment="Create initial history"
    )

    session.add(title)

    try:
        session.flush()
    except IntegrityError as exc:
        if isinstance(exc.orig, UniqueViolation):
            raise RecordAlreadyExistsError(
                f"Title with name {payload.name} already exists"
            ) from exc
        logger.exception("Unknown exception encountered while creating title")
        raise

    if create_event:
        create_title_modified_event(
            session, action="created", title_name=title.name, title_id=title.id
        )

    return title


def create_title_history_entry(
    session: OrmSession, title: Title, author_id: UUID, comment: str | None = None
) -> TitleHistory:
    history_entry = TitleHistory(
        name=title.name,
        title=title.title,
        comment=comment,
        creator=title.creator,
        publisher=title.publisher,
        description=title.description,
        language=title.language,
        illustration_48x48_at_1=title.illustration_48x48_at_1,
        long_description=title.long_description,
        license=title.license,
        relation=title.relation,
        source=title.source,
        maturity=title.maturity,
        archived=title.archived,
        flavours=get_title_flavours(title),
        collection_titles=[
            {
                "collection_name": ct.collection.name,
                "path": str(ct.path),
            }
            for ct in title.collections
        ],
    )
    history_entry.title_ = title
    history_entry.author_id = author_id
    session.add(history_entry)
    return history_entry


def update_title(
    session: OrmSession,
    *,
    title_identifier: str,
    author_id: UUID,
    payload: TitleUpdateSchema,
    create_event: bool = True,
) -> Title:
    """Update a title's details

    When collection_titles changes:
    - Finds all books associated with this title where location_kind == 'prod'
    - Updates their locations according to the new collection configuration
    - Sets the needs_file_operation flag to true for these books
    """
    title = get_title(session, title_identifier)

    # Return early if no update data
    if not payload.model_dump(exclude_unset=True, mode="json"):
        return title

    # Determine whether to permit update based on value of archived parameter
    if payload.archived is None and title.archived:
        raise RecordDoesNotExistError("Title is archived")

    if payload.archived is True and title.archived:
        raise RecordDoesNotExistError("Title is already archived.")

    if payload.archived is False and not title.archived:
        raise RecordDoesNotExistError("Title is not archived.")

    update_data = payload.model_dump(
        exclude_unset=True,
        exclude={"collection_titles", "comment", "flavours"},
        mode="json",
    )
    name_changed = payload.name is not None and payload.name != title.name

    if update_data:
        try:
            title = session.scalars(
                update(Title)
                .where(Title.id == title.id)
                .values(**update_data)
                .returning(Title)
            ).one()
        except IntegrityError as exc:
            raise RecordAlreadyExistsError(
                f"Title with name '{payload.name}' already exists"
            ) from exc

    # Determine if collection titles changed
    collection_titles_changed = False

    if payload.collection_titles is not None:
        if len(title.collections) != len(payload.collection_titles):
            collection_titles_changed = True
        else:
            current_collections: set[str] = {
                f"{tc.collection.name}:{tc.path}" for tc in title.collections
            }
            new_collections: set[str] = {
                f"{entry.collection_name}:{entry.path}"
                for entry in payload.collection_titles
            }

            if current_collections != new_collections:
                collection_titles_changed = True

    if collection_titles_changed and payload.collection_titles is not None:
        # Remove existing collection_titles
        for tc in title.collections:
            session.delete(tc)

        title.collections.clear()
        session.flush()

        for entry in payload.collection_titles:
            collection = get_collection_by_name(
                session, collection_name=entry.collection_name
            )

            collection_title = CollectionTitle(path=Path(entry.path))
            collection_title.collection = collection
            collection_title.title = title

            session.add(collection_title)

        # If collection_titles changed, update book locations for prod books
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

    if payload.flavours is not None:
        pass
        # update_zimfarm_recipe(
        #     session,
        #     recipe=title.zimfarm_recipes[0],
        #     flavours=payload.flavours,
        #     title=title,
        #     current_recipes={
        #         zimfarm_recipe.id for zimfarm_recipe in title.zimfarm_recipes
        #     },
        #     create_event=False,
        # )

    if name_changed and create_event:
        create_title_modified_event(
            session, action="updated", title_name=title.name, title_id=title.id
        )

    for book in title.books:
        update_book_issues(session, book)

    create_title_history_entry(session, title, author_id, payload.comment)

    return get_title_by_id(session, title_id=title.id)


def archive_title(
    session: OrmSession,
    title_identifier: str,
    author_id: UUID,
) -> Title:
    """Mark a title as archived.

    All books belonging to the title are marked for deletion immediately
    """
    title = update_title(
        session,
        author_id=author_id,
        title_identifier=title_identifier,
        payload=TitleUpdateSchema(archived=True),
    )

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
        title.events.append(f"{getnow()}: marked books in title for deletion.")

    session.add(title)
    session.flush()

    return title


def archive_titles(
    session: OrmSession,
    *,
    author_id: UUID,
    title_names: list[str],
) -> None:
    """Archive a list of titles"""
    for title_name in title_names:
        archive_title(session, title_name, author_id)


def restore_title(
    session: OrmSession,
    title_identifier: str,
    author_id: UUID,
) -> Title:
    """Remove a title from the archive status.

    Restores books belonging to title that have not been deleted.
    """

    title = update_title(
        session,
        author_id=author_id,
        title_identifier=title_identifier,
        payload=TitleUpdateSchema(archived=False),
    )
    now = getnow()
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
    session: OrmSession, *, title_names: list[str], author_id: UUID
) -> None:
    """Restore a list of archived titles"""
    for title_name in title_names:
        restore_title(session, title_name, author_id)


def create_title_history_schema(entry: TitleHistory) -> TitleHistorySchema:
    return TitleHistorySchema(
        id=entry.id,
        created_at=entry.created_at,
        archived=entry.archived,
        name=entry.name,
        maturity=entry.maturity,
        author=entry.author.display_name,
        title=entry.title,
        creator=entry.creator,
        publisher=entry.publisher,
        description=entry.description,
        language=entry.language,
        illustration_48x48_at_1=entry.illustration_48x48_at_1,
        long_description=entry.long_description,
        license=entry.license,
        relation=entry.relation,
        source=entry.source,
        flavours=entry.flavours,
        comment=entry.comment,
        collections=[
            BaseTitleCollectionSchema(
                collection_name=collection["collection_name"], path=collection["path"]
            )
            for collection in entry.collection_titles
        ],
    )


def get_title_history(
    session: OrmSession, *, title_identifier: str, skip: int, limit: int
) -> ListResult[TitleHistorySchema]:
    """Get a title's history"""
    title = get_title(session, title_identifier)
    stmt = (
        select(TitleHistory)
        .where(TitleHistory.title_id == title.id)
        .options(selectinload(TitleHistory.author))
        .order_by(TitleHistory.created_at.desc())
    )
    return ListResult[TitleHistorySchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_title_history_schema(entry)
            for entry in session.scalars(stmt.offset(skip).limit(limit)).all()
        ],
    )


def get_title_history_entry_or_none(
    session: OrmSession, *, title_identifier: str, history_id: UUID
) -> TitleHistory | None:
    """Get a title's history entry or None if it does not exist"""
    title = get_title(session, title_identifier)
    return session.scalars(
        select(TitleHistory).where(
            TitleHistory.id == history_id, TitleHistory.title_id == title.id
        )
    ).one_or_none()


def get_title_history_entry(
    session: OrmSession, *, title_identifier: str, history_id: UUID
) -> TitleHistory:
    """Get a title's history entry"""
    if history_entry := get_title_history_entry_or_none(
        session, title_identifier=title_identifier, history_id=history_id
    ):
        return history_entry
    raise RecordDoesNotExistError(
        f"Title '{title_identifier}' does not have a history entry with id {history_id}"
    )


def revert_title(
    session: OrmSession,
    *,
    title_identifier: str,
    history_id: UUID,
    author_id: UUID,
    comment: str | None = None,
) -> Title:
    """Revert the title configuration and settings to those defined in history_id"""
    entry = get_title_history_entry(
        session, title_identifier=title_identifier, history_id=history_id
    )
    title = update_title(
        session,
        title_identifier=title_identifier,
        author_id=author_id,
        payload=TitleUpdateSchema(
            comment=comment,
            name=entry.name,
            maturity=cast(Literal["unstable", "stable"], entry.maturity),
            collection_titles=[
                BaseTitleCollectionSchema(
                    collection_name=collection["collection_name"],
                    path=collection["path"],
                )
                for collection in entry.collection_titles
            ],
            long_description=entry.long_description,
            license=entry.license,
            relation=entry.relation,
            source=entry.source,
            title=entry.title,
            creator=entry.creator,
            description=entry.description,
            publisher=entry.publisher,
            language=entry.language,
            illustration_48x48_at_1=entry.illustration_48x48_at_1,
            flavours=entry.flavours,
        ),
    )
    return title


def merge_titles(
    session: OrmSession, target_title_name: str, source_title_names: list[str]
) -> None:
    """
    Merge list of titles in sources to the target title.

    - Books belonging to the source titles are associated with the target title.
    - The source titles are deleted along with their collection titles
    - Books are re-processed as if they are new
    """
    if not source_title_names:
        raise ValueError("No sources to merge from")

    if target_title_name in source_title_names:
        raise ValueError("Target title must not be in the list of sources")

    source_titles = [
        get_title_by_name(session, name=source_title_name)
        for source_title_name in source_title_names
    ]
    target_title = get_title_by_name(session, name=target_title_name)
    source_books = [book for title in source_titles for book in title.books]
    # Attach all the books to the new title
    for source_book in source_books:
        source_book.title = target_title
        session.add(source_book)

    for source_title in source_titles:
        for collection_title in source_title.collections:
            session.delete(collection_title)
        session.delete(source_title)

    for source_book in source_books:
        process_book(session, source_book)

    apply_retention_rules(session, target_title)
