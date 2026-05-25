from pathlib import Path
from typing import NamedTuple, cast
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordAlreadyExistsError, RecordDoesNotExistError
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
)
from cms_backend.db.warehouse import get_warehouse
from cms_backend.schemas.models import CollectionUpdateSchema
from cms_backend.schemas.orms import (
    CollectionFullSchema,
    CollectionLightSchema,
    ListResult,
)
from cms_backend.utils import is_valid_uuid


def get_collection_or_none(session: OrmSession, library_id: UUID) -> Collection | None:
    """Get a collection by ID if possible else None"""
    return session.scalars(
        select(Collection).where(Collection.id == library_id)
    ).one_or_none()


def get_collection(session: OrmSession, library_id: UUID) -> Collection:
    """Get a collection by ID if possible else raise an exception"""
    if (collection := get_collection_or_none(session, library_id=library_id)) is None:
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
        raise RecordDoesNotExistError(f"Collection '{collection_name} does not exist")
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
    )


def create_collection(
    session: OrmSession,
    *,
    name: str,
    warehouse_name: str,
    download_base_url: str | None = None,
    view_base_url: str | None,
) -> Collection:
    warehouse = get_warehouse(session, warehouse_name)
    collection = Collection(
        name=name,
        download_base_url=download_base_url,
        view_base_url=view_base_url,
        warehouse_id=warehouse.id,
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
    return collection


def update_collection(
    session: OrmSession, *, collection_id: str, request: CollectionUpdateSchema
) -> Collection:
    """Update a collection"""
    if is_valid_uuid(collection_id):
        collection = get_collection(session, UUID(collection_id))
    else:
        collection = get_collection_by_name(session, collection_id)

    values = request.model_dump(exclude_unset=True)
    if not values:
        return collection

    try:
        session.execute(
            update(Collection).values(**values).where(Collection.id == collection.id)
        )
    except IntegrityError as exc:
        if isinstance(exc.orig, UniqueViolation):
            raise RecordAlreadyExistsError(
                f"Collection with name {request.name} already exists"
            ) from exc
        logger.exception("Unknown exception encountered while creating collection")
        raise

    session.refresh(collection)
    return collection
