from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Book, BookLocation, Library, LibraryWarehousePath


def get_library_or_none(session: OrmSession, library_id: UUID) -> Library | None:
    """Get a library by ID if possible else None"""
    return session.scalars(
        select(Library).where(Library.id == library_id)
    ).one_or_none()


def get_library(session: OrmSession, library_id: UUID) -> Library:
    """Get a library by ID if possible else raise an exception"""
    if (library := get_library_or_none(session, library_id=library_id)) is None:
        raise RecordDoesNotExistError(f"Library with ID {library_id} does not exist")
    return library


def get_library_by_name_or_none(
    session: OrmSession, library_name: str
) -> Library | None:
    """Get a library by name if possible else None"""
    return session.scalars(
        select(Library).where(Library.name == library_name)
    ).one_or_none()


def get_latest_books_for_library(session: OrmSession, library_id: UUID) -> list[Book]:
    """
    Get the latest book for each name+flavour combination in a library.

    A library contains multiple warehouse paths. For each unique name+flavour
    combination found in the library's warehouse paths, return only the most
    recent published book (by created_at).

    Args:
        session: ORM session
        library_id: ID of the library

    Returns:
        List of Book objects, one per name+flavour combination
    """
    # Get all books in the library's warehouse paths that are published
    # and currently located there
    stmt = (
        select(Book)
        .join(BookLocation)
        .join(
            LibraryWarehousePath,
            BookLocation.warehouse_path_id == LibraryWarehousePath.warehouse_path_id,
        )
        .where(
            and_(
                LibraryWarehousePath.library_id == library_id,
                BookLocation.status == "current",
                Book.status == "published",
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
