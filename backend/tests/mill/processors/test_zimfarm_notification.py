"""Tests for zimfarm notification processor."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Warehouse, ZimfarmNotification
from cms_backend.mill.processors.zimfarm_notification import process_notification

VALID_NOTIFICATION_CONTENT = {
    "article_count": 1000,
    "media_count": 500,
    "size": 1000000,
    "metadata": {
        "Name": "test_en_all",
        "Title": "Test Article",
        "Creator": "Test Creator",
        "Publisher": "Test Publisher",
        "Date": "2025-01-01",
        "Description": "Test description",
        "Language": "eng",
    },
    "zimcheck": {"status": "passed"},
    "folder_name": "test_folder",
    "filename": "test.zim",
}


def test_process_notification_missing_mandatory_keys(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test that notification with missing mandatory keys is marked as
    bad_notification"""
    # Missing article_count and media_count
    content = {
        "size": 1000000,
        "metadata": {"Name": "test"},
        "zimcheck": {},
        "folder_name": "test",
        "filename": "test.zim",
    }

    notification = create_zimfarm_notification(content=content)
    dbsession.flush()

    with patch("cms_backend.mill.processors.zimfarm_notification.process_book"):
        process_notification(dbsession, notification)

    assert notification.status == "bad_notification"
    assert any("missing mandatory keys" in event for event in notification.events)
    assert "article_count" in notification.events[0]
    assert "media_count" in notification.events[0]


def test_process_notification_invalid_filename(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test that notification with invalid filename is marked as bad_notification"""
    content = VALID_NOTIFICATION_CONTENT.copy()
    content["filename"] = 123  # Invalid: should be string

    notification = create_zimfarm_notification(content=content)
    dbsession.flush()

    with patch("cms_backend.mill.processors.zimfarm_notification.process_book"):
        process_notification(dbsession, notification)

    assert notification.status == "bad_notification"
    assert any(
        "filename must be a non-empty string" in event for event in notification.events
    )


def test_process_notification_invalid_folder_name(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test that notification with invalid folder_name is marked as bad_notification"""
    content = VALID_NOTIFICATION_CONTENT.copy()
    content["folder_name"] = None  # type: ignore[assignment]  # Invalid: should be string

    notification = create_zimfarm_notification(content=content)
    dbsession.flush()

    with patch("cms_backend.mill.processors.zimfarm_notification.process_book"):
        process_notification(dbsession, notification)

    assert notification.status == "bad_notification"
    assert any(
        "folder_name must be a non-empty string" in event
        for event in notification.events
    )


def test_process_notification_valid_creates_book_and_location(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that valid notification creates book and location,
    then calls process_book"""
    # Create the jail warehouse that MillContext expects
    jail_warehouse = create_warehouse(name="jail")
    dbsession.flush()

    notification = create_zimfarm_notification(content=VALID_NOTIFICATION_CONTENT)
    dbsession.flush()

    # Mock MillContext to use our test warehouse
    mock_context = MagicMock()
    mock_context.jail_warehouse_id = jail_warehouse.id
    mock_context.jail_base_path = Path("/jail")

    with patch(
        "cms_backend.mill.processors.zimfarm_notification.MillContext", mock_context
    ):
        with patch(
            "cms_backend.mill.processors.zimfarm_notification.process_book"
        ) as mock_process_book:
            process_notification(dbsession, notification)

    # Notification should be marked as processed
    assert notification.status == "processed"

    # process_book should have been called
    mock_process_book.assert_called_once()
    called_book = mock_process_book.call_args[0][1]

    # Book should be created with correct properties
    assert called_book.id == notification.id
    assert called_book.article_count == VALID_NOTIFICATION_CONTENT["article_count"]
    assert called_book.media_count == VALID_NOTIFICATION_CONTENT["media_count"]
    assert called_book.size == VALID_NOTIFICATION_CONTENT["size"]
    assert called_book.zim_metadata == VALID_NOTIFICATION_CONTENT["metadata"]
    assert called_book.zimcheck_result == VALID_NOTIFICATION_CONTENT["zimcheck"]

    # Book should have a location in jail warehouse
    assert len(called_book.locations) == 1
    location = called_book.locations[0]
    assert location.filename == VALID_NOTIFICATION_CONTENT["filename"]
    assert location.status == "current"
    assert location.warehouse_id == jail_warehouse.id

    # Notification should have events
    assert any(
        "created from Zimfarm notification" in event for event in called_book.events
    )


def test_process_notification_error_handling(
    dbsession: OrmSession,
    create_zimfarm_notification: Callable[..., ZimfarmNotification],
):
    """Test that errors during processing are caught and status is set to errored"""
    notification = create_zimfarm_notification(content=VALID_NOTIFICATION_CONTENT)
    dbsession.flush()

    with patch(
        "cms_backend.mill.processors.zimfarm_notification.process_book",
        side_effect=Exception("Test error"),
    ):
        process_notification(dbsession, notification)

    assert notification.status == "errored"
    assert any(
        "error encountered while processing notification" in event
        for event in notification.events
    )
