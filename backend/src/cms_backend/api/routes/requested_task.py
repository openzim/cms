from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import get_accessible_collection_ids
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db import requested_task as db_requested_task
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import TaskInfo
from cms_backend.schemas.orms import RequestedTaskLightSchema
from cms_backend.utils.requests import fetch_task_from_zimfarm

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TasksGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    collection_id: UUID | None = None
    status: list[NotEmptyString] | None = None


@router.get("")
def get_tasks(
    params: Annotated[TasksGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> ListResponse[RequestedTaskLightSchema]:
    """Get a list of tasks"""

    results = db_requested_task.get_requested_tasks(
        session,
        skip=params.skip,
        limit=params.limit,
        status=params.status,
        accessible_collection_ids=accessible_collection_ids,
        sort_order="desc",
    )

    return ListResponse[RequestedTaskLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get(
    "/{task_id}",
)
def get_task(
    task_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> TaskInfo:
    """Fetch details about a task."""
    zimfarm_task = fetch_task_from_zimfarm(task_id)
    db_requested_task.update_task_status(
        session,
        task_id,
        zimfarm_task.status,
        accessible_collection_ids=accessible_collection_ids,
    )
    return zimfarm_task
