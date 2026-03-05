from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Event
from cms_backend.utils.datetime import getnow


def create_title_modified_event(
    session: OrmSession, *, action: str, title_name: str, title_id: UUID
) -> Event:
    """Create an event for title modifications."""
    event = Event(
        created_at=getnow(),
        topic="title_modified",
        payload={"id": str(title_id), "name": title_name, "action": action},
    )
    session.add(event)
    session.flush()
    return event


def get_next_event_to_process_or_none(
    session: OrmSession,
    topic: str,
) -> Event | None:
    return session.scalars(
        select(Event).where(Event.topic == topic).order_by(Event.created_at).limit(1)
    ).one_or_none()


def delete_event(session: OrmSession, event_id: UUID):
    """Delete an event from the database"""
    session.execute(delete(Event).where(Event.id == event_id))
