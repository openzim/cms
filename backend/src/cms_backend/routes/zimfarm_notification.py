from datetime import datetime
from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
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
from cms_backend.schemas import BaseModel, WithExtraModel

router = APIRouter(prefix="/zimfarm-notification")


# only thing we wanna validate from the Zimfarm notification is that it has an ID
# which is an UUID and we do not already received it
class ZimfarmNotificationSchema(WithExtraModel):
    id: UUID


class ZimfarmNotificationLightSchema(BaseModel):
    id: UUID
    received_at: datetime
    content: dict[str, Any]
    processed: bool


@router.post("")
async def create_zimfarm_notification(
    request: ZimfarmNotificationSchema,
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
) -> ZimfarmNotificationLightSchema:
    """Create a zimfarm notification"""

    db_notification = db_get_zimfarm_notification(
        session=session, notification_id=notification_id
    )

    return ZimfarmNotificationLightSchema(
        id=db_notification.id,
        received_at=db_notification.received_at,
        content=db_notification.content,
        processed=db_notification.processed,
    )
