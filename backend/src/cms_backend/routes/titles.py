from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import gen_dbsession
from cms_backend.db.title import create_title as db_create_title
from cms_backend.db.title import get_titles as db_get_titles
from cms_backend.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import TitleLightSchema

router = APIRouter(prefix="/titles", tags=["titles"])


class TitlesGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None


class TitleCreateSchema(BaseModel):
    name: str
    producer_unique_id: str
    producer_display_name: str | None = None
    producer_display_url: str | None = None
    dev_warehouse_path_id: UUID
    prod_warehouse_path_id: UUID
    in_prod: bool = False


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


@router.post("")
def create_title(
    title_data: TitleCreateSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> TitleLightSchema:
    """Create a new title"""
    title = db_create_title(
        session,
        name=title_data.name,
        producer_unique_id=title_data.producer_unique_id,
        producer_display_name=title_data.producer_display_name,
        producer_display_url=title_data.producer_display_url,
        dev_warehouse_path_id=title_data.dev_warehouse_path_id,
        prod_warehouse_path_id=title_data.prod_warehouse_path_id,
        in_prod=title_data.in_prod,
    )
    return TitleLightSchema(
        id=title.id,
        name=title.name,
        producer_unique_id=title.producer_unique_id,
        producer_display_name=title.producer_display_name,
        producer_display_url=title.producer_display_url,
    )
