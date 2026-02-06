from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    Title,
)
from cms_backend.schemas.orms import CollectionLightSchema, ListResult


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


def get_latest_books_for_collection(
    session: OrmSession, collection_id: UUID
) -> list[Book]:
    """
    Get the latest published book for each name+flavour combination in a collection.

    A collection contains many books, this function return only the most recently
     published book (by created_at) for each name+flavour combination.

    Args:
        session: ORM session
        collection_id: ID of the collection

    Returns:
        List of Book objects, one per name+flavour combination
    """
    # Get all books in the library's warehouse paths that are published
    # and currently located there
    stmt = (
        select(Book)
        .join(BookLocation)
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle)
        .join(Collection)
        .where(
            and_(
                BookLocation.status == "current",
                BookLocation.warehouse_id == Collection.warehouse_id,
                BookLocation.path == CollectionTitle.path,
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
                Collection.id == collection_id,
            )
        )
        .order_by(Book.name, Book.flavour, Book.created_at.desc())
    )

    books = session.scalars(stmt).all()

    # Filter to keep only the latest book per name+flavour combination
    seen: set[tuple[str | None, str | None]] = set()
    latest_books: list[Book] = []
    for book in books:
        key = (book.name, book.flavour)
        if key not in seen:
            seen.add(key)
            latest_books.append(book)

    return latest_books


def get_collections(
    session: OrmSession, *, skip: int, limit: int
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
        .outerjoin(CollectionTitle)
        .group_by(Collection.id)
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
