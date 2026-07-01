from pathlib import Path
from typing import NamedTuple, cast
from uuid import UUID

from psycopg.errors import UniqueViolation
from pydantic import AnyUrl
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordAlreadyExistsError, RecordDoesNotExistError
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionHistory,
    CollectionTitle,
    Title,
)
from cms_backend.db.warehouse import get_warehouse
from cms_backend.schemas.models import CollectionUpdateSchema
from cms_backend.schemas.orms import (
    CollectionFullSchema,
    CollectionHistorySchema,
    CollectionLightSchema,
    ListResult,
)
from cms_backend.utils import is_valid_uuid


def get_collection_by_id_or_none(
    session: OrmSession, library_id: UUID
) -> Collection | None:
    """Get a collection by ID if possible else None"""
    return session.scalars(
        select(Collection).where(Collection.id == library_id)
    ).one_or_none()


def get_collection_by_id(session: OrmSession, library_id: UUID) -> Collection:
    """Get a collection by ID if possible else raise an exception"""
    if (
        collection := get_collection_by_id_or_none(session, library_id=library_id)
    ) is None:
        raise RecordDoesNotExistError(f"Collection with ID {library_id} does not exist")
    return collection


def get_collection_by_name_or_none(
    session: OrmSession, collection_name: str
) -> Collection | None:
    """Get a collection by name if possible else None"""
    return session.scalars(
        select(Collection).where(Collection.name == collection_name)
    ).one_or_none()


def get_collection_by_name(session: OrmSession, collection_name: str) -> Collection:
    """Get a collection by name if possible else raise an exception"""
    if (
        collection := get_collection_by_name_or_none(
            session, collection_name=collection_name
        )
    ) is None:
        raise RecordDoesNotExistError(f"Collection '{collection_name}' does not exist")
    return collection


def get_collection_or_none(
    session: OrmSession, collection_identifier: str
) -> Collection | None:
    """Get a collection by it's name or ID if possible else None"""
    if is_valid_uuid(collection_identifier):
        collection = get_collection_by_id_or_none(session, UUID(collection_identifier))
    else:
        collection = get_collection_by_name_or_none(session, collection_identifier)
    return collection


def get_collection(session: OrmSession, collection_identifier: str) -> Collection:
    collection = get_collection_or_none(session, collection_identifier)
    if collection is None:
        raise RecordDoesNotExistError(
            f"Collection '{collection_identifier}' does not exist"
        )
    return collection


class LibraryBookData(NamedTuple):
    """Tuple containing book alongside other data needed for library rendering."""

    book: Book
    title: Title
    download_base_url: str | None
    path: Path
    filename: str


def get_latest_books_for_collection(
    session: OrmSession, collection_id: UUID
) -> list[LibraryBookData]:
    """
    Get the latest published book for each name+flavour combination in a collection.

    A collection contains many books, this function return only the most recently
     published book (by created_at) for each name+flavour combination.

    Args:
        session: ORM session
        collection_id: ID of the collection

    Returns:
        List of LibraryBookData objects, one per name+flavour combination
    """
    # Get all books in the library's warehouse paths that are published
    # and currently located there
    stmt = (
        select(
            Book,
            Title,
            Collection.download_base_url,
            CollectionTitle.path.label("subpath"),
            BookLocation.filename,
        )
        .join(BookLocation)
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle)
        .join(Collection)
        .where(
            and_(
                Book.location_kind == "prod",
                BookLocation.status == "current",
                BookLocation.warehouse_id == Collection.warehouse_id,
                BookLocation.path == CollectionTitle.path,
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
                Collection.id == collection_id,
                BookLocation.is_backup.is_(False),
            )
        )
        .order_by(Title.id, Book.flavour, Book.created_at.desc())
    )
    # Filter to keep only the latest book per name+flavour combination
    seen: set[tuple[UUID, str | None]] = set()
    latest_books: list[LibraryBookData] = []
    for row in session.execute(stmt).all():
        book = cast(Book, row.Book)
        title = cast(Title, row.Title)
        key = (title.id, book.flavour)
        if key not in seen:
            seen.add(key)
            latest_books.append(
                LibraryBookData(
                    book=book,
                    title=title,
                    path=row.subpath,
                    download_base_url=row.download_base_url,
                    filename=row.filename,
                )
            )

    return latest_books


def get_collections(
    session: OrmSession, *, name: str | None = None, skip: int, limit: int
) -> ListResult[CollectionLightSchema]:
    """Get the list of collections."""
    stmt = (
        select(
            Collection.id,
            Collection.name,
            func.coalesce(
                func.array_agg(func.distinct(CollectionTitle.path)).filter(
                    CollectionTitle.path.is_not(None)
                ),
                [],
            ).label("paths"),
        )
        .where(
            # If a client provides an argument i.e it is not None,
            # we compare the corresponding model field against the argument,
            # otherwise, we compare the argument to its default which translates
            # to a SQL true i.e we don't filter based on this argument (a no-op).
            (
                Collection.name.ilike(f"%{name if name is not None else ''}%")
                | (name is None)
            ),
        )
        .outerjoin(CollectionTitle)
        .group_by(Collection.id)
        .order_by(Collection.name.desc())
    )

    return ListResult[CollectionLightSchema](
        nb_records=count_from_stmt(session, select(Collection.id)),
        records=[
            CollectionLightSchema(
                id=collection_id,
                name=collection_name,
                paths=paths,
            )
            for collection_id, collection_name, paths in session.execute(
                stmt.offset(skip).limit(limit)
            ).all()
        ],
    )


def create_collection_full_schema(collection: Collection) -> CollectionFullSchema:
    return CollectionFullSchema(
        id=collection.id,
        warehouse=collection.warehouse.name,
        name=collection.name,
        download_base_url=collection.download_base_url,
        view_base_url=collection.view_base_url,
        article_count_increase_threshold=collection.article_count_increase_threshold,
        media_count_increase_threshold=collection.media_count_increase_threshold,
        article_count_decrease_threshold=collection.article_count_decrease_threshold,
        media_count_decrease_threshold=collection.media_count_decrease_threshold,
    )


def create_collection_history_entry(
    session: OrmSession,
    collection: Collection,
    author_id: UUID,
    comment: str | None = None,
) -> CollectionHistory:
    history_entry = CollectionHistory(
        name=collection.name,
        comment=comment,
        download_base_url=collection.download_base_url,
        view_base_url=collection.view_base_url,
        article_count_increase_threshold=collection.article_count_increase_threshold,
        media_count_increase_threshold=collection.media_count_increase_threshold,
        article_count_decrease_threshold=collection.article_count_decrease_threshold,
        media_count_decrease_threshold=collection.media_count_decrease_threshold,
    )
    history_entry.collection = collection
    history_entry.author_id = author_id
    session.add(history_entry)
    return history_entry


def create_collection(
    session: OrmSession,
    *,
    name: str,
    author_id: UUID,
    warehouse_name: str,
    download_base_url: str | None = None,
    view_base_url: str | None = None,
    article_count_increase_threshold: float | None = None,
    media_count_increase_threshold: float | None = None,
    article_count_decrease_threshold: float | None = None,
    media_count_decrease_threshold: float | None = None,
) -> Collection:
    warehouse = get_warehouse(session, warehouse_name)
    collection = Collection(
        name=name,
        download_base_url=download_base_url,
        view_base_url=view_base_url,
        warehouse_id=warehouse.id,
        article_count_increase_threshold=article_count_increase_threshold,
        article_count_decrease_threshold=article_count_decrease_threshold,
        media_count_increase_threshold=media_count_increase_threshold,
        media_count_decrease_threshold=media_count_decrease_threshold,
    )
    session.add(collection)
    try:
        session.flush()
    except IntegrityError as exc:
        if isinstance(exc.orig, UniqueViolation):
            raise RecordAlreadyExistsError(
                f"Collection with name {name} already exists"
            ) from exc
        logger.exception("Unknown exception encountered while creating collection")
        raise
    create_collection_history_entry(
        session, collection, author_id, comment="Create initial history"
    )
    return collection


def update_collection(
    session: OrmSession,
    *,
    collection_id: str,
    author_id: UUID,
    request: CollectionUpdateSchema,
) -> Collection:
    """Update a collection"""
    collection = get_collection(session, collection_id)

    values = request.model_dump(exclude_unset=True, exclude={"comment"}, mode="json")
    if not values:
        return collection

    try:
        collection = session.scalars(
            update(Collection)
            .values(**values)
            .where(Collection.id == collection.id)
            .returning(Collection)
        ).one()
    except IntegrityError as exc:
        if isinstance(exc.orig, UniqueViolation):
            raise RecordAlreadyExistsError(
                f"Collection with name {request.name} already exists"
            ) from exc
        logger.exception("Unknown exception encountered while creating collection")
        raise

    create_collection_history_entry(session, collection, author_id, request.comment)
    return collection


def create_collection_history_schema(
    entry: CollectionHistory,
) -> CollectionHistorySchema:
    return CollectionHistorySchema(
        id=entry.id,
        created_at=entry.created_at,
        comment=entry.comment,
        name=entry.name,
        download_base_url=entry.download_base_url,
        view_base_url=entry.view_base_url,
        author=entry.author.display_name,
        article_count_increase_threshold=entry.article_count_increase_threshold,
        article_count_decrease_threshold=entry.article_count_decrease_threshold,
        media_count_increase_threshold=entry.media_count_increase_threshold,
        media_count_decrease_threshold=entry.media_count_decrease_threshold,
    )


def get_collection_history(
    session: OrmSession, *, collection_id: str, skip: int, limit: int
) -> ListResult[CollectionHistorySchema]:
    """Get a collection's history"""
    collection = get_collection(session, collection_id)
    stmt = (
        select(CollectionHistory)
        .where(CollectionHistory.collection_id == collection.id)
        .options(selectinload(CollectionHistory.author))
        .order_by(CollectionHistory.created_at.desc())
    )
    return ListResult[CollectionHistorySchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            create_collection_history_schema(entry)
            for entry in session.scalars(stmt.offset(skip).limit(limit)).all()
        ],
    )


def get_collection_history_entry_or_none(
    session: OrmSession, *, collection_id: str, history_id: UUID
) -> CollectionHistory | None:
    """Get a collecton's history entry or None if it does not exist"""
    collection = get_collection(session, collection_id)
    return session.scalars(
        select(CollectionHistory).where(
            CollectionHistory.id == history_id,
            CollectionHistory.collection_id == collection.id,
        )
    ).one_or_none()


def get_collection_history_entry(
    session: OrmSession, *, collection_id: str, history_id: UUID
) -> CollectionHistory:
    """Get a book's history entry"""
    if history_entry := get_collection_history_entry_or_none(
        session, collection_id=collection_id, history_id=history_id
    ):
        return history_entry
    raise RecordDoesNotExistError(
        f"Collection '{collection_id}' does not have a history entry with id "
        f"{history_id}"
    )


def revert_collection(
    session: OrmSession,
    *,
    collection_id: str,
    history_id: UUID,
    author_id: UUID,
    comment: str | None = None,
) -> Collection:
    """Revert the collection configuration to those defined in history_id"""
    entry = get_collection_history_entry(
        session, collection_id=collection_id, history_id=history_id
    )
    collection = update_collection(
        session,
        author_id=author_id,
        collection_id=str(collection_id),
        request=CollectionUpdateSchema(
            name=entry.name,
            comment=comment,
            download_base_url=AnyUrl(entry.download_base_url)
            if entry.download_base_url
            else None,
            view_base_url=AnyUrl(entry.view_base_url) if entry.view_base_url else None,
            article_count_increase_threshold=entry.article_count_increase_threshold,
            article_count_decrease_threshold=entry.article_count_decrease_threshold,
            media_count_increase_threshold=entry.media_count_increase_threshold,
            media_count_decrease_threshold=entry.media_count_decrease_threshold,
        ),
    )

    return collection
