from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import not_, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import ZimfarmNotification
from cms_backend.schemas.orms import ListResult, ZimfarmNotificationLightSchema
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


def get_zimfarm_notifications(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    has_book: bool | None = None,
    has_errored: bool | None = None,
    is_processed: bool | None = None,
    received_after: datetime | None = None,
    received_before: datetime | None = None,
) -> ListResult[ZimfarmNotificationLightSchema]:
    """Get a list of zimfarm notification"""

    stmt = select(
        ZimfarmNotification.id,
        ZimfarmNotification.book_id,
        ZimfarmNotification.processed,
        ZimfarmNotification.errored,
        ZimfarmNotification.received_at,
    ).order_by(ZimfarmNotification.received_at)

    if has_book is not None:
        if has_book:
            stmt = stmt.where(ZimfarmNotification.book_id.is_not(None))
        else:
            stmt = stmt.where(ZimfarmNotification.book_id.is_(None))

    if has_errored is not None:
        stmt = stmt.where(ZimfarmNotification.errored == has_errored)

    if is_processed is not None:
        stmt = stmt.where(ZimfarmNotification.processed == is_processed)

    if received_after is not None:
        stmt = stmt.where(ZimfarmNotification.received_at > received_after)

    if received_before is not None:
        stmt = stmt.where(ZimfarmNotification.received_at < received_before)

    return ListResult[ZimfarmNotificationLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            ZimfarmNotificationLightSchema(
                id=notif_id,
                book_id=notif_book_id,
                processed=notif_processed,
                errored=notif_errored,
                received_at=notif_received_at,
            )
            for (
                notif_id,
                notif_book_id,
                notif_processed,
                notif_errored,
                notif_received_at,
            ) in session.execute(stmt.offset(skip).limit(limit)).all()
        ],
    )
