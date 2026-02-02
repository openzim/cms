from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.title import create_title as db_create_title
from cms_backend.db.title import get_title_by_id as db_get_title_by_id
from cms_backend.db.title import get_titles as db_get_titles
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import (
    BookLightSchema,
    TitleCollectionSchema,
    TitleFullSchema,
    TitleLightSchema,
)

router = APIRouter(prefix="/titles", tags=["titles"])


class TitlesGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None


class TitleCreateSchema(BaseModel):
    name: str
    maturity: str | None = None


@router.get("")
def get_titles(
    params: Annotated[TitlesGetSchema, Query()],
    session: OrmSession = Depends(gen_dbsession),
) -> ListResponse[TitleLightSchema]:
    results = db_get_titles(
        session,
        skip=params.skip,
        limit=params.limit,
        name=params.name,
    )
    return ListResponse[TitleLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get("/{title_id}")
def get_title(
    title_id: UUID,
    session: OrmSession = Depends(gen_dbsession),
) -> TitleFullSchema:
    """Get a title by ID with full details including books"""
    title = db_get_title_by_id(session, title_id=title_id)

    return TitleFullSchema(
        id=title.id,
        name=title.name,
        maturity=title.maturity,
        events=title.events,
        books=[
            BookLightSchema(
                id=book.id,
                title_id=book.title_id,
                needs_processing=book.needs_processing,
                has_error=book.has_error,
                needs_file_operation=book.needs_file_operation,
                location_kind=book.location_kind,
                created_at=book.created_at,
                name=book.name,
                date=book.date,
                flavour=book.flavour,
            )
            for book in title.books
        ],
        collections=[
            TitleCollectionSchema(
                collection_id=tc.collection_id,
                collection_name=tc.collection.name,
                path=str(tc.path),
            )
            for tc in title.collections
        ],
    )


@router.post("")
def create_title(
    title_data: TitleCreateSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> TitleLightSchema:
    """Create a new title"""
    title = db_create_title(
        session,
        name=title_data.name,
        maturity=title_data.maturity,
    )
    return TitleLightSchema(
        id=title.id,
        name=title.name,
        maturity=title.maturity,
    )
