from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.books import get_book as db_get_book
from cms_backend.db.books import get_books as db_get_books
from cms_backend.db.books import get_zim_urls as db_get_zim_urls
from cms_backend.schemas import BaseModel
from cms_backend.schemas.models import ZimUrlsSchema
from cms_backend.schemas.orms import (
    BookFullSchema,
    BookLightSchema,
    BookLocationSchema,
)

router = APIRouter(prefix="/books", tags=["books"])


class BooksGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    id: NotEmptyString | None = None
    has_title: bool | None = None
    needs_processing: bool | None = None
    has_error: bool | None = None
    needs_file_operation: bool | None = None
    location_kinds: list[NotEmptyString] | None = None


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


@router.get("/{book_id}")
def get_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookFullSchema:
    """Get a book by ID"""

    db_book = db_get_book(session=session, book_id=book_id)

    # Separate current and target locations
    current_locations = [
        BookLocationSchema(
            warehouse_name=location.warehouse.name,
            path=str(location.path),
            filename=location.filename,
            status=location.status,
        )
        for location in db_book.locations
        if location.status == "current"
    ]

    target_locations = [
        BookLocationSchema(
            warehouse_name=location.warehouse.name,
            path=str(location.path),
            filename=location.filename,
            status=location.status,
        )
        for location in db_book.locations
        if location.status == "target"
    ]

    return BookFullSchema(
        id=db_book.id,
        title_id=db_book.title_id,
        needs_processing=db_book.needs_processing,
        has_error=db_book.has_error,
        needs_file_operation=db_book.needs_file_operation,
        location_kind=db_book.location_kind,
        created_at=db_book.created_at,
        name=db_book.name,
        date=db_book.date,
        flavour=db_book.flavour,
        article_count=db_book.article_count,
        media_count=db_book.media_count,
        size=db_book.size,
        zimcheck_result=db_book.zimcheck_result,
        zim_metadata=db_book.zim_metadata,
        events=db_book.events,
        current_locations=current_locations,
        target_locations=target_locations,
    )


@router.get("/zims")
def get_zim_urls(
    zim_ids: Annotated[list[UUID], Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ZimUrlsSchema:
    return db_get_zim_urls(session, zim_ids)
