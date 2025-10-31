from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import gen_dbsession
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
