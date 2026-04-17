from typing import cast

from sqlalchemy import and_, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db.collection import LibraryBookData
from cms_backend.db.models import (
    Book,
    BookLocation,
)


def get_staging_books_library_data(session: OrmSession) -> list[LibraryBookData]:
    """
    Get the list of library data for all books in staging.

    Args:
        session: ORM session

    Returns:
        List of LibraryBookData objects for each book in staging.
    """
    # Get all books in the library's warehouse paths that are published
    # and currently located there
    stmt = (
        select(
            Book,
            BookLocation.filename,
        )
        .join(BookLocation)
        .where(
            and_(
                Book.location_kind == "staging",
                BookLocation.status == "current",
                BookLocation.warehouse_id == Context.staging_warehouse_id,
                BookLocation.path == Context.staging_base_path,
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
            )
        )
        .order_by(Book.created_at.desc())
    )
    return [
        LibraryBookData(
            book=cast(Book, row.Book),
            path=Context.staging_base_path,
            download_base_url=Context.staging_download_base_url,
            filename=row.filename,
        )
        for row in session.execute(stmt).all()
    ]
