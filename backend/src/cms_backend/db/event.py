from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Event
from cms_backend.schemas.orms import EventLightSchema, ListResult
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


def get_events(
    session: OrmSession, *, skip: int, limit: int, topic: str | None = None
) -> ListResult[EventLightSchema]:
    """Get a list of events."""
    stmt = (
        select(
            func.count().over().label("nb_records"),
            Event.id.label("event_id"),
            Event.created_at.label("created_at"),
            Event.topic.label("event_topic"),
        )
        .where(
            (Event.topic.ilike(f"%{topic if topic is not None else ''}%"))
            | (topic is None),
        )
        .offset(skip)
        .limit(limit)
        .order_by(Event.created_at.desc())
    )
    result = ListResult[EventLightSchema](nb_records=0, records=[])
    for nb_records, event_id, created_at, event_topic in session.execute(stmt).all():
        result.nb_records = nb_records
        result.records.append(
            EventLightSchema(
                id=event_id,
                created_at=created_at,
                topic=event_topic,
            )
        )
    return result
