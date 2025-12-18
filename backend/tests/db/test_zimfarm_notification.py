from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Book, ZimfarmNotification
from cms_backend.db.zimfarm_notification import (
    create_zimfarm_notification as db_create_zimfarm_notification,
)
from cms_backend.db.zimfarm_notification import (
    get_next_notification_to_process_or_none,
    get_zimfarm_notification,
    get_zimfarm_notification_or_none,
    get_zimfarm_notifications,
)
from cms_backend.utils.datetime import getnow

# Example notification content for testing
GOOD_NOTIFICATION_CONTENT = {
    "requested_task_id": "test-task-123",
    "status": "success",
}


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
    assert result == zimfarm_notification


def test_create_zimfarm_notification(dbsession: OrmSession, faker: Faker):
    """Create a notification"""
    notification_id = uuid4()
    content = {"foo": " ".join(faker.words())}
    created_notification = db_create_zimfarm_notification(
        dbsession, notification_id=notification_id, content=content
    )
    assert created_notification is not None
    assert created_notification.id == notification_id
    received_since = (getnow() - created_notification.received_at).total_seconds()
    assert received_since > 0
    assert received_since < 3600
    assert created_notification.id == notification_id
    assert created_notification.content == content


def test_get_next_notification_to_process_or_none(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    notification = create_zimfarm_notification(content=GOOD_NOTIFICATION_CONTENT)
    assert notification.status == "pending"
    next_notification = get_next_notification_to_process_or_none(dbsession)
    assert next_notification == notification
    next_notification = get_next_notification_to_process_or_none(dbsession)
    assert (
        next_notification == notification
    )  # still same retrieved since still not processed
    assert next_notification is not None
    next_notification.status = "processed"
    next_notification = get_next_notification_to_process_or_none(dbsession)
    assert next_notification is None


@pytest.mark.parametrize(
    "has_book,status,expected_count",
    [
        pytest.param(None, None, 10, id="all-no-filters"),
        pytest.param(True, None, 4, id="has-book-only"),
        pytest.param(False, None, 6, id="no-book-only"),
        pytest.param(None, "errored", 4, id="errored-only"),
        pytest.param(None, "processed", 2, id="processed-only"),
        pytest.param(None, "bad_notification", 2, id="bad-notification-only"),
        pytest.param(None, "pending", 2, id="pending-only"),
        pytest.param(True, "errored", 2, id="has-book-and-errored"),
        pytest.param(True, "processed", 2, id="has-book-and-processed"),
        pytest.param(False, "pending", 2, id="no-book-and-pending"),
    ],
)
def test_get_zimfarm_notifications_filters(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    create_book: Callable[..., Book],
    has_book: bool | None,
    status: str | None,
    expected_count: int,
):
    """Test that get_zimfarm_notifications works correctly with various filters"""
    now = getnow()

    # Create notifications with different characteristics
    # Notification 0: has_book, status=errored
    notif0 = create_zimfarm_notification(received_at=now - timedelta(hours=10))
    notif0.status = "errored"
    book0 = create_book(zimfarm_notification=notif0)
    notif0.book_id = book0.id

    # Notification 1: has_book, status=errored
    notif1 = create_zimfarm_notification(received_at=now - timedelta(hours=9))
    notif1.status = "errored"
    book1 = create_book(zimfarm_notification=notif1)
    notif1.book_id = book1.id

    # Notification 2: has_book, status=processed
    notif2 = create_zimfarm_notification(received_at=now - timedelta(hours=8))
    notif2.status = "processed"
    book2 = create_book(zimfarm_notification=notif2)
    notif2.book_id = book2.id

    # Notification 3: no_book, status=errored
    notif3 = create_zimfarm_notification(received_at=now - timedelta(hours=7))
    notif3.status = "errored"

    # Notification 4: no_book, status=errored
    notif4 = create_zimfarm_notification(received_at=now - timedelta(hours=6))
    notif4.status = "errored"

    # Notification 5: no_book, status=bad_notification
    notif5 = create_zimfarm_notification(received_at=now - timedelta(hours=5))
    notif5.status = "bad_notification"

    # Notification 6: no_book, status=bad_notification
    notif6 = create_zimfarm_notification(received_at=now - timedelta(hours=4))
    notif6.status = "bad_notification"

    # Notification 7: no_book, status=pending
    notif7 = create_zimfarm_notification(received_at=now - timedelta(hours=3))
    notif7.status = "pending"

    # Notification 8: no_book, status=pending
    notif8 = create_zimfarm_notification(received_at=now - timedelta(hours=2))
    notif8.status = "pending"

    # Notification 9: has_book, status=processed
    notif9 = create_zimfarm_notification(received_at=now - timedelta(hours=1))
    notif9.status = "processed"
    book9 = create_book(zimfarm_notification=notif9)
    notif9.book_id = book9.id

    dbsession.flush()

    limit = 20
    results = get_zimfarm_notifications(
        dbsession,
        skip=0,
        limit=limit,
        has_book=has_book,
        status=status,
    )
    assert results.nb_records == expected_count
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


@pytest.mark.parametrize(
    "received_after_hours,received_before_hours,expected_count",
    [
        pytest.param(None, None, 5, id="no-time-filters"),  # All 5 notifications match
        pytest.param(
            6, None, 2, id="received-after-6h"
        ),  # Last 2 (4h, 2h ago) - exclusive
        pytest.param(
            None, 3, 4, id="received-before-3h"
        ),  # First 4 (10h, 8h, 6h, 4h ago) - exclusive
        pytest.param(8, 3, 2, id="received-between-8h-and-3h"),  # Middle 2 (6h, 4h ago)
    ],
)
def test_get_zimfarm_notifications_time_filters(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    received_after_hours: int | None,
    received_before_hours: int | None,
    expected_count: int,
):
    """Test that get_zimfarm_notifications works correctly with time filters"""
    now = getnow()

    # Create 5 notifications at different times
    create_zimfarm_notification(received_at=now - timedelta(hours=10))
    create_zimfarm_notification(received_at=now - timedelta(hours=8))
    create_zimfarm_notification(received_at=now - timedelta(hours=6))
    create_zimfarm_notification(received_at=now - timedelta(hours=4))
    create_zimfarm_notification(received_at=now - timedelta(hours=2))

    dbsession.flush()

    received_after = (
        now - timedelta(hours=received_after_hours) if received_after_hours else None
    )
    received_before = (
        now - timedelta(hours=received_before_hours) if received_before_hours else None
    )

    results = get_zimfarm_notifications(
        dbsession,
        skip=0,
        limit=20,
        received_after=received_after,
        received_before=received_before,
    )
    assert results.nb_records == expected_count
    assert len(results.records) == expected_count


@pytest.mark.parametrize(
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 3, 2, id="third-page-partial"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 8, id="first-page-with-high-limit"),
    ],
)
def test_get_zimfarm_notifications_skip(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_zimfarm_notifications works correctly with skip and limit"""
    now = getnow()

    # Create 8 notifications
    for i in range(8):
        create_zimfarm_notification(received_at=now - timedelta(hours=10 - i))

    dbsession.flush()

    results = get_zimfarm_notifications(
        dbsession,
        skip=skip,
        limit=limit,
    )
    assert results.nb_records == 8
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


@pytest.mark.parametrize(
    "notification_id_filter,expected_count,expected_ids",
    [
        pytest.param("1234-5678-1234", 1, ["notif1"], id="partial-match-notif1"),
        pytest.param("8765-4321", 1, ["notif2"], id="partial-match-notif2"),
        pytest.param("2222-3333", 1, ["notif3"], id="partial-match-notif3"),
        pytest.param("1234", 1, ["notif1"], id="match-1234-only-notif1"),
        pytest.param("abcd", 1, ["notif4"], id="lowercase-match"),
        pytest.param("ABCD", 1, ["notif4"], id="uppercase-match"),
        pytest.param("AbCd", 1, ["notif4"], id="mixed-case-match"),
        pytest.param("nonexistent", 0, [], id="no-match"),
        pytest.param("aaaa", 2, ["notif5", "notif6"], id="multiple-matches"),
        pytest.param("1111", 2, ["notif3", "notif5"], id="multiple-matches-with-1111"),
    ],
)
def test_get_zimfarm_notifications_notification_id_filter(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    notification_id_filter: str,
    expected_count: int,
    expected_ids: list[str],
):
    """Test that get_zimfarm_notifications works with notification_id filter"""
    from uuid import UUID

    # Create notifications with specific UUIDs
    notif_mapping = {
        "notif1": create_zimfarm_notification(
            _id=UUID("12345678-1234-5678-1234-567812345678"),
            content={"test": "notif1"},
        ),
        "notif2": create_zimfarm_notification(
            _id=UUID("87654321-4321-8765-4321-876543218765"),
            content={"test": "notif2"},
        ),
        "notif3": create_zimfarm_notification(
            _id=UUID("11111111-2222-3333-4444-555555555555"),
            content={"test": "notif3"},
        ),
        "notif4": create_zimfarm_notification(
            _id=UUID("abcdefab-cdef-abcd-efab-cdefabcdefab"),
            content={"test": "notif4"},
        ),
        "notif5": create_zimfarm_notification(
            _id=UUID("aaaaaaaa-1111-1111-1111-111111111111"),
            content={"test": "notif5"},
        ),
        "notif6": create_zimfarm_notification(
            _id=UUID("aaaaaaaa-2222-2222-2222-222222222222"),
            content={"test": "notif6"},
        ),
    }

    dbsession.flush()

    results = get_zimfarm_notifications(
        dbsession,
        skip=0,
        limit=20,
        notification_id=notification_id_filter,
    )

    assert results.nb_records == expected_count
    assert len(results.records) == expected_count

    # Verify the correct notifications were returned
    returned_ids = {str(record.id) for record in results.records}
    expected_uuid_ids = {str(notif_mapping[key].id) for key in expected_ids}
    assert returned_ids == expected_uuid_ids


def test_get_zimfarm_notifications_notification_id_combined_with_other_filters(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    create_book: Callable[..., Book],
):
    """Test notification_id filter combined with other filters"""
    from uuid import UUID

    # Create notifications with specific characteristics
    notif1 = create_zimfarm_notification(
        _id=UUID("aaaaaaaa-1111-1111-1111-111111111111"),
        content={"test": "notif1"},
    )
    notif1.status = "processed"
    book1 = create_book(zimfarm_notification=notif1)
    notif1.book_id = book1.id

    notif2 = create_zimfarm_notification(
        _id=UUID("aaaaaaaa-2222-2222-2222-222222222222"),
        content={"test": "notif2"},
    )
    notif2.status = "pending"

    notif3 = create_zimfarm_notification(
        _id=UUID("bbbbbbbb-3333-3333-3333-333333333333"),
        content={"test": "notif3"},
    )
    notif3.status = "bad_notification"

    dbsession.flush()

    # Filter by ID pattern "aaaa" - should match notif1 and notif2
    results = get_zimfarm_notifications(
        dbsession, skip=0, limit=20, notification_id="aaaa"
    )
    assert results.nb_records == 2

    # Filter by ID pattern "aaaa" AND status=processed - should only match notif1
    results = get_zimfarm_notifications(
        dbsession, skip=0, limit=20, notification_id="aaaa", status="processed"
    )
    assert results.nb_records == 1
    assert results.records[0].id == notif1.id

    # Filter by ID pattern "aaaa" AND has_book=false - should only match notif2
    results = get_zimfarm_notifications(
        dbsession, skip=0, limit=20, notification_id="aaaa", has_book=False
    )
    assert results.nb_records == 1
    assert results.records[0].id == notif2.id

    # Filter by ID pattern "bbbb" AND status=bad_notification - should only match notif3
    results = get_zimfarm_notifications(
        dbsession, skip=0, limit=20, notification_id="bbbb", status="bad_notification"
    )
    assert results.nb_records == 1
    assert results.records[0].id == notif3.id
