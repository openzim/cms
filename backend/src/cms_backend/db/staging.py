from collections.abc import Sequence
from pathlib import Path
from typing import cast
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db.collection import LibraryBookData
from cms_backend.db.models import (
    Book,
    BookLocation,
    CollectionTitle,
    Title,
)


def get_staging_books_library_data(
    session: OrmSession, *, accessible_collection_ids: Sequence[UUID] | None = None
) -> list[LibraryBookData]:
    """
    Get the list of library data for all books in staging.

    Only returns books whose title belongs to at least one of the
    accessible_collection_ids.

    Args:
        session: ORM session
        accessible_collection_ids: IDs of collections the caller can access

    Returns:
        List of LibraryBookData objects for each book in staging.
    """
    # Get all books in the library's warehouse paths that are published
    # and currently located there
    stmt = (
        select(
            Book,
            Title,
            BookLocation.filename,
        )
        .join(BookLocation)
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle, CollectionTitle.title_id == Title.id, isouter=True)
        .where(
            and_(
                Book.location_kind == "staging",
                BookLocation.status == "current",
                BookLocation.warehouse_id == Context.staging_warehouse_id,
                BookLocation.path == Context.staging_base_path,
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
                BookLocation.is_backup.is_(False),
                CollectionTitle.collection_id.in_(accessible_collection_ids or [])
                | (accessible_collection_ids is None),
            )
        )
        .order_by(Book.created_at.desc())
    )
    return [
        LibraryBookData(
            book=cast(Book, row.Book),
            title=cast(Title, row.Title),
            # staging download url is supposed to contain the whole path already
            # for convenience in deployment
            path=Path(""),
            download_base_url=Context.staging_download_base_url,
            filename=row.filename,
        )
        for row in session.execute(stmt).all()
    ]
