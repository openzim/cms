from uuid import UUID

from pydantic import AnyUrl
from sqlalchemy import String, and_, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import Book, BookLocation, Collection, CollectionTitle, Title
from cms_backend.schemas.models import ZimUrlSchema, ZimUrlsSchema
from cms_backend.schemas.orms import BookLightSchema, ListResult
from cms_backend.utils.filename import construct_download_url


def get_book_or_none(session: OrmSession, book_id: UUID) -> Book | None:
    """Get a book by ID if possible else None"""
    return session.scalars(
        select(Book)
        .where(Book.id == book_id)
        .options(selectinload(Book.title), selectinload(Book.zimfarm_notification))
    ).one_or_none()


def get_book(session: OrmSession, book_id: UUID) -> Book:
    """Get a book by ID if possible else raise an exception"""
    if (book := get_book_or_none(session, book_id=book_id)) is None:
        raise RecordDoesNotExistError(f"Book with ID {book_id} does not exist")
    return book


def get_books(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    book_id: str | None = None,
    has_title: bool | None = None,
    needs_processing: bool | None = None,
    has_error: bool | None = None,
    needs_file_operation: bool | None = None,
    location_kinds: list[str] | None = None,
) -> ListResult[BookLightSchema]:
    """Get a list of books"""

    stmt = select(
        Book.id,
        Book.title_id,
        Book.needs_processing,
        Book.has_error,
        Book.needs_file_operation,
        Book.location_kind,
        Book.created_at,
        Book.name,
        Book.date,
        Book.flavour,
    ).order_by(Book.id)

    if book_id is not None:
        stmt = stmt.where(Book.id.cast(String).ilike(f"%{book_id}%"))

    if has_title is not None:
        if has_title:
            stmt = stmt.where(Book.title_id.is_not(None))
        else:
            stmt = stmt.where(Book.title_id.is_(None))

    if needs_processing is not None:
        stmt = stmt.where(Book.needs_processing == needs_processing)

    if has_error is not None:
        stmt = stmt.where(Book.has_error == has_error)

    if needs_file_operation is not None:
        stmt = stmt.where(Book.needs_file_operation == needs_file_operation)

    if location_kinds is not None:
        stmt = stmt.where(Book.location_kind.in_(location_kinds))

    return ListResult[BookLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            BookLightSchema(
                id=book_id_result,
                title_id=book_title_id,
                needs_processing=needs_processing,
                has_error=has_error,
                needs_file_operation=needs_file_operation,
                location_kind=location_kind,
                created_at=created_at,
                name=name,
                date=date,
                flavour=flavour,
            )
            for (
                book_id_result,
                book_title_id,
                needs_processing,
                has_error,
                needs_file_operation,
                location_kind,
                created_at,
                name,
                date,
                flavour,
            ) in session.execute(stmt.offset(skip).limit(limit)).all()
        ],
    )


def get_zim_urls(session: OrmSession, zim_ids: list[UUID]) -> ZimUrlsSchema:
    """
    Get view and download URLs for a list of ZIM IDs (Book IDs).
    """
    stmt = (
        select(
            Book.id.label("book_id"),
            Collection.name.label("collection_name"),
            Collection.download_base_url,
            Collection.view_base_url,
            CollectionTitle.path.label("subpath"),
            BookLocation.filename,
        )
        .join(Title, Book.title_id == Title.id)
        .join(CollectionTitle, CollectionTitle.title_id == Title.id)
        .join(Collection, Collection.id == CollectionTitle.collection_id)
        .join(
            BookLocation,
            and_(
                BookLocation.book_id == Book.id,
                BookLocation.status == "current",
                BookLocation.warehouse_id == Collection.warehouse_id,
                BookLocation.path == CollectionTitle.path,
            ),
        )
        .where(
            and_(
                Book.id.in_(zim_ids),
                Book.needs_processing.is_(False),
                Book.has_error.is_(False),
                Book.needs_file_operation.is_(False),
            )
        )
    )

    result = ZimUrlsSchema(urls={zim_id: [] for zim_id in zim_ids})

    for row in session.execute(stmt).all():
        if row.download_base_url:
            result.urls[row.book_id].append(
                ZimUrlSchema(
                    kind="download",
                    url=AnyUrl(
                        construct_download_url(
                            row.download_base_url, row.subpath, row.filename
                        )
                    ),
                    collection=row.collection_name,
                )
            )

        if row.view_base_url:
            filename_without_suffix = (
                row.filename[:-4] if row.filename.endswith(".zim") else row.filename
            )
            result.urls[row.book_id].append(
                ZimUrlSchema(
                    kind="view",
                    url=AnyUrl(f"{row.view_base_url}/viewer#{filename_without_suffix}"),
                    collection=row.collection_name,
                )
            )

    return result
