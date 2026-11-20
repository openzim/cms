from collections.abc import Sequence
from pathlib import Path
from typing import cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import aliased

from cms_backend.context import Context
from cms_backend.db.collection import LibraryBookData
from cms_backend.db.models import (
    Book,
    BookLocation,
    BookTransitionStatus,
    CollectionTitle,
    Illustration,
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
    title_illustration = aliased(Illustration)
    book_illustration = aliased(Illustration)
    stmt = (
        select(
            Book,
            Title,
            BookLocation.filename,
            func.coalesce(title_illustration.data, book_illustration.data).label(
                "illustration_data"
            ),
            func.coalesce(
                title_illustration.hex_digest, book_illustration.hex_digest
            ).label("illustration_hex_digest"),
        )
        .join(BookLocation)
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle, CollectionTitle.title_id == Title.id, isouter=True)
        .outerjoin(
            title_illustration,
            title_illustration.hex_digest == Title.illustration_48x48_at_1,
        )
        .outerjoin(
            book_illustration,
            book_illustration.hex_digest
            == Book.zim_metadata["Illustration_48x48@1_hex_digest"].astext,
        )
        .where(
            and_(
                Book.location_kind == "staging",
                BookLocation.status == "current",
                BookLocation.warehouse_id == Context.staging_warehouse_id,
                BookLocation.path == Context.staging_base_path,
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
                or_(
                    Book.transition_status.is_(None),
                    Book.transition_status
                    == BookTransitionStatus.CHECKING_LIBRARY.value,
                ),
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
            illustration_data=row.illustration_data,
            illustration_hex_digest=row.illustration_hex_digest,
        )
        for row in session.execute(stmt).all()
    ]
