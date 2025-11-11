from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import gen_dbsession
from cms_backend.db.books import get_book as db_get_book
from cms_backend.db.books import get_books as db_get_books
from cms_backend.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import (
    BookFullSchema,
    BookLightSchema,
    BookLocationSchema,
    ProducerSchema,
)

router = APIRouter(prefix="/books", tags=["books"])


class BooksGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    id: NotEmptyString | None = None
    has_title: bool | None = None
    status: NotEmptyString | None = None


@router.get("")
async def get_books(
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
        status=params.status,
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
async def get_book(
    book_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> BookFullSchema:
    """Get a book by ID"""

    db_book = db_get_book(session=session, book_id=book_id)

    # Separate current and target locations
    current_locations = [
        BookLocationSchema(
            warehouse_path_id=location.warehouse_path_id,
            warehouse_name=location.warehouse_path.warehouse.name,
            folder_name=location.warehouse_path.folder_name,
            filename=location.filename,
            status=location.status,
        )
        for location in db_book.locations
        if location.status == "current"
    ]

    target_locations = [
        BookLocationSchema(
            warehouse_path_id=location.warehouse_path_id,
            warehouse_name=location.warehouse_path.warehouse.name,
            folder_name=location.warehouse_path.folder_name,
            filename=location.filename,
            status=location.status,
        )
        for location in db_book.locations
        if location.status == "target"
    ]

    return BookFullSchema(
        id=db_book.id,
        title_id=db_book.title_id,
        status=db_book.status,
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
        producer=ProducerSchema(
            display_name=db_book.producer_display_name,
            display_url=db_book.producer_display_url,
            unique_id=db_book.producer_unique_id,
        ),
        current_locations=current_locations,
        target_locations=target_locations,
    )
