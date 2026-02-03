from datetime import datetime
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.api.routes.dependencies import require_permission
from cms_backend.api.routes.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.zimfarm_notification import (
    create_zimfarm_notification as db_create_zimfarm_notification,
)
from cms_backend.db.zimfarm_notification import (
    get_zimfarm_notification as db_get_zimfarm_notification,
)
from cms_backend.db.zimfarm_notification import (
    get_zimfarm_notification_or_none as db_get_zimfarm_notification_or_none,
)
from cms_backend.db.zimfarm_notification import (
    get_zimfarm_notifications as db_get_zimfarm_notifications,
)
from cms_backend.schemas import BaseModel, WithExtraModel
from cms_backend.schemas.orms import (
    ZimfarmNotificationFullSchema,
    ZimfarmNotificationLightSchema,
)

router = APIRouter(prefix="/zimfarm-notifications", tags=["zimfarm-notifications"])


class ZimfarmNotificationsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    id: NotEmptyString | None = None
    has_book: bool | None = None
    status: str | None = None
    received_after: datetime | None = None
    received_before: datetime | None = None


# only thing we wanna validate from the Zimfarm notification is that it has an ID
# which is an UUID and we do not already received it
class ZimfarmNotificationCreateSchema(WithExtraModel):
    id: UUID


@router.get("")
async def get_zimfarm_notifications(
    params: Annotated[ZimfarmNotificationsGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[ZimfarmNotificationLightSchema]:
    """Get a list of zimfarm notifications"""

    results = db_get_zimfarm_notifications(
        session,
        skip=params.skip,
        limit=params.limit,
        notification_id=params.id,
        has_book=params.has_book,
        status=params.status,
        received_after=params.received_after,
        received_before=params.received_before,
    )

    return ListResponse[ZimfarmNotificationLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.post(
    "",
    dependencies=[
        Depends(require_permission(namespace="zimfarm_notification", name="create"))
    ],
)
async def create_zimfarm_notification(
    request: ZimfarmNotificationCreateSchema,
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> Response:
    """Create a zimfarm notification"""

    if db_get_zimfarm_notification_or_none(session=session, notification_id=request.id):
        logger.warning(f"Ignoring duplicate Zimfarm notification for id {request.id}")
        return Response(status_code=HTTPStatus.ACCEPTED)

    content = request.model_dump()
    content.pop("id")
    db_create_zimfarm_notification(
        session,
        notification_id=request.id,
        content=content,
    )

    return Response(status_code=HTTPStatus.ACCEPTED)


@router.get("/{notification_id}")
async def get_zimfarm_notification(
    notification_id: Annotated[UUID, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ZimfarmNotificationFullSchema:
    """Create a zimfarm notification"""

    db_notification = db_get_zimfarm_notification(
        session=session, notification_id=notification_id
    )

    return ZimfarmNotificationFullSchema(
        id=db_notification.id,
        book_id=db_notification.book_id,
        status=db_notification.status,
        received_at=db_notification.received_at,
        content=db_notification.content,
        events=db_notification.events,
    )
