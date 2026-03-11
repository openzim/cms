from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.event import get_events as db_get_events
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import EventLightSchema

router = APIRouter(prefix="/events", tags=["events"])


class EventsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    topic: NotEmptyString | None = None


@router.get("")
def get_events(
    params: Annotated[EventsGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[EventLightSchema]:
    """Get a list of events"""

    results = db_get_events(
        session, skip=params.skip, limit=params.limit, topic=params.topic
    )
    return ListResponse[EventLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )
