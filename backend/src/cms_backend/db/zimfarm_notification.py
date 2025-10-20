from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import ZimfarmNotification
from cms_backend.utils.datetime import getnow


def create_zimfarm_notification(
    session: OrmSession, *, notification_id: UUID, content: str
) -> ZimfarmNotification:
    """Create a new Zimfarm notification"""

    zimfarm_notification = ZimfarmNotification(
        id=notification_id, received_at=getnow(), content=content, processed=False
    )

    session.add(zimfarm_notification)
    session.flush()

    return zimfarm_notification


def get_zimfarm_notification_or_none(
    session: OrmSession, notification_id: UUID
) -> ZimfarmNotification | None:
    """Get a schedule for the given schedule name if possible else None"""
    return session.scalars(
        select(ZimfarmNotification)
        .where(ZimfarmNotification.id == notification_id)
        .options(selectinload(ZimfarmNotification.book))
    ).one_or_none()


def get_zimfarm_notification(
    session: OrmSession, notification_id: UUID
) -> ZimfarmNotification:
    """Get a schedule for the given schedule name if possible else raise an exception"""
    if (
        schedule := get_zimfarm_notification_or_none(
            session, notification_id=notification_id
        )
    ) is None:
        raise RecordDoesNotExistError(
            f"Zimfarm Notification with ID {notification_id} does not exist"
        )
    return schedule
