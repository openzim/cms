from typing import Any
from uuid import UUID

from sqlalchemy import not_, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import ZimfarmNotification
from cms_backend.utils.datetime import getnow


def create_zimfarm_notification(
    session: OrmSession, *, notification_id: UUID, content: dict[str, Any]
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
    """Get a zimfarm notification by ID if possible else None"""
    return session.scalars(
        select(ZimfarmNotification)
        .where(ZimfarmNotification.id == notification_id)
        .options(selectinload(ZimfarmNotification.book))
    ).one_or_none()


def get_zimfarm_notification(
    session: OrmSession, notification_id: UUID
) -> ZimfarmNotification:
    """Get a zimfarm notification by ID if possible else raise an exception"""
    if (
        schedule := get_zimfarm_notification_or_none(
            session, notification_id=notification_id
        )
    ) is None:
        raise RecordDoesNotExistError(
            f"Zimfarm Notification with ID {notification_id} does not exist"
        )
    return schedule


def get_next_notification_to_process_or_none(
    session: OrmSession,
) -> ZimfarmNotification | None:
    return session.scalars(
        select(ZimfarmNotification)
        .where(not_(ZimfarmNotification.processed))
        .order_by(ZimfarmNotification.received_at)
        .limit(1)
    ).one_or_none()
