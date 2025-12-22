from uuid import UUID

from sqlalchemy import String, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import Book
from cms_backend.schemas.orms import BookLightSchema, ListResult


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
    location_kind: str | None = None,
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

    if location_kind is not None:
        stmt = stmt.where(Book.location_kind == location_kind)

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
