from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import require_permission
from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.book import create_book_full_schema
from cms_backend.db.book import delete_book as db_delete_book
from cms_backend.db.book import get_book as db_get_book
from cms_backend.db.book import move_book as db_move_book
from cms_backend.db.book import recover_book as db_recover_book
from cms_backend.db.books import get_books as db_get_books
from cms_backend.db.books import get_zim_urls as db_get_zim_urls
from cms_backend.schemas import BaseModel
from cms_backend.schemas.models import ZimUrlsSchema
from cms_backend.schemas.orms import (
    BookFullSchema,
    BookLightSchema,
)

router = APIRouter(prefix="/books", tags=["books"])


class BookMoveSchema(BaseModel):
    destination: Literal["prod", "staging"]


class BooksGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    id: NotEmptyString | None = None
    has_title: bool | None = None
    needs_processing: bool | None = None
    has_error: bool | None = None
    needs_file_operation: bool | None = None
    location_kinds: list[NotEmptyString] | None = None
    needs_attention: bool | None = None


@router.get("")
def get_books(
    params: Annotated[BooksGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[BookLightSchema]:
    """Get a list of books"""

    results = db_get_books(
        session,
        skip=params.skip,
        limit=params.limit,
        book_id=params.id,
        has_title=params.has_title,
        needs_processing=params.needs_processing,
        has_error=params.has_error,
        needs_file_operation=params.needs_file_operation,
        location_kinds=params.location_kinds,
        needs_attention=params.needs_attention,
    )

    return ListResponse[BookLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get("/zims")
def get_zim_urls(
    zim_ids: Annotated[list[UUID], Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ZimUrlsSchema:
    return db_get_zim_urls(session, zim_ids)


@router.get("/{book_id}")
def get_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookFullSchema:
    """Get a book by ID"""
    return create_book_full_schema(db_get_book(session=session, book_id=book_id))


@router.delete(
    "/{book_id}",
    dependencies=[Depends(require_permission(namespace="book", name="delete"))],
)
def delete_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    *,
    force_delete: Annotated[bool, Query()] = False,
) -> BookFullSchema:
    return create_book_full_schema(
        db_delete_book(session, book_id=book_id, force_delete=force_delete)
    )


@router.post(
    "/{book_id}/recover",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def recover_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookFullSchema:
    return create_book_full_schema(db_recover_book(session, book_id=book_id))


@router.post(
    "/{book_id}/move",
    dependencies=[Depends(require_permission(namespace="book", name="update"))],
)
def move_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    request: BookMoveSchema,
) -> BookFullSchema:
    return create_book_full_schema(
        db_move_book(session, book_id=book_id, destination=request.destination)
    )
