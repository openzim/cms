from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.event import (
    create_title_modified_event,
    delete_event,
    get_next_event_to_process_or_none,
)
from cms_backend.db.models import Event


@pytest.mark.parametrize(
    "action",
    [pytest.param("updated", id="updated"), pytest.param("created", id="created")],
)
def test_create_title_modified_eventaction(dbsession: OrmSession, action: str):
    """Test creating a title_modified event with action"""
    title_id = uuid4()
    title_name = "wikipedia_en_all"

    event = create_title_modified_event(
        dbsession, action=action, title_name=title_name, title_id=title_id
    )

    assert event.topic == "title_modified"
    assert event.payload["id"] == str(title_id)
    assert event.payload["name"] == title_name
    assert event.payload["action"] == action


def test_get_next_event_to_process_or_none_returns_none_when_empty(
    dbsession: OrmSession,
):
    """Test get_next_event_to_process_or_none returns None when no events exist"""
    event = get_next_event_to_process_or_none(dbsession, topic="title_modified")
    assert event is None


def test_get_next_event_to_process_or_none_returns_single_event(
    dbsession: OrmSession,
):
    """Test get_next_event_to_process_or_none returns the event when only one exists"""
    created_event = create_title_modified_event(
        dbsession, action="created", title_name="test", title_id=uuid4()
    )
    dbsession.flush()

    event = get_next_event_to_process_or_none(dbsession, topic="title_modified")
    assert event is not None
    assert event.id == created_event.id
    assert event.payload["action"] == "created"


def test_delete_event(
    dbsession: OrmSession,
):
    """Test deleting an event from the database"""
    event = create_title_modified_event(
        dbsession, action="created", title_name="test", title_id=uuid4()
    )

    delete_event(dbsession, event.id)
    assert (
        dbsession.scalars(select(Event).where(Event.id == event.id)).one_or_none()
        is None
    )
