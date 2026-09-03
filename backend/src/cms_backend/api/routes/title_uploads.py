from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import get_accessible_collection_ids
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db import title_upload as db_title_upload
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import TaskInfo
from cms_backend.schemas.orms import TitleUploadLightSchema
from cms_backend.utils.requests import fetch_task_from_zimfarm

router = APIRouter(prefix="/title-uploads", tags=["title-uploads"])


class TitleUploadsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    title_id: UUID | None = None
    status: list[NotEmptyString] | None = None


@router.get("")
def get_title_uploads(
    params: Annotated[TitleUploadsGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> ListResponse[TitleUploadLightSchema]:
    """Get a list of title uploads for a title"""

    results = db_title_upload.get_title_uploads(
        session,
        skip=params.skip,
        limit=params.limit,
        status=params.status,
        accessible_collection_ids=accessible_collection_ids,
        title_id=params.title_id,
        sort_order="desc",
    )

    return ListResponse[TitleUploadLightSchema](
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
def get_title_upload(
    task_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> TaskInfo:
    """Fetch details about a title upload."""
    zimfarm_task = fetch_task_from_zimfarm(task_id)
    db_title_upload.update_title_upload_status(
        session,
        task_id,
        zimfarm_task.status,
        accessible_collection_ids=accessible_collection_ids,
    )
    return zimfarm_task
