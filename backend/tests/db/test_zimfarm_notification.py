from uuid import uuid4

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import ZimfarmNotification
from cms_backend.db.zimfarm_notification import (
    create_zimfarm_notification,
    get_zimfarm_notification,
    get_zimfarm_notification_or_none,
)
from cms_backend.utils.datetime import getnow


def test_get_zimfarm_notification_or_none_(
    dbsession: OrmSession,
    zimfarm_notification: ZimfarmNotification,  # noqa: ARG001 - needed for conftest
):
    """Returns None if the notification does not exists"""
    result = get_zimfarm_notification_or_none(dbsession, notification_id=uuid4())
    assert result is None


def test_get_zimfarm_notification_not_found(
    dbsession: OrmSession,
    zimfarm_notification: ZimfarmNotification,  # noqa: ARG001 - needed for conftest
):
    """Raises an exception if the user does not exist"""
    with pytest.raises(RecordDoesNotExistError):
        get_zimfarm_notification(dbsession, notification_id=uuid4())


def test_get_zimfarm_notification_exist(
    dbsession: OrmSession, zimfarm_notification: ZimfarmNotification
):
    """Returns the notification if it exists"""
    result = get_zimfarm_notification(
        dbsession, notification_id=zimfarm_notification.id
    )
    assert result is not None
    assert result.id == zimfarm_notification.id


def test_create_zimfarm_notification(dbsession: OrmSession, faker: Faker):
    """Create a notification"""
    notification_id = uuid4()
    content = {"foo": " ".join(faker.words())}
    created_notification = create_zimfarm_notification(
        dbsession, notification_id=notification_id, content=content
    )
    assert created_notification is not None
    assert created_notification.id == notification_id
    received_since = (getnow() - created_notification.received_at).total_seconds()
    assert received_since > 0
    assert received_since < 3600
    assert created_notification.id == notification_id
    assert created_notification.content == content
