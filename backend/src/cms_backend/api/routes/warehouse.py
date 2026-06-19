from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import gen_dbsession
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db.warehouse import get_warehouses as db_get_warehouses
from cms_backend.schemas.fields import LimitFieldMax200, SkipField

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("")
def get_warehouses(
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
):
    """Get a list of warehouses"""
    result = db_get_warehouses(session, skip=skip, limit=limit)
    return ListResponse(
        items=result.records,
        meta=calculate_pagination_metadata(
            nb_records=result.nb_records,
            skip=skip,
            limit=limit,
            page_size=len(result.records),
        ),
    )
