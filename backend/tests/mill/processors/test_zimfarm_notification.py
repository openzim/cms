"""Integration tests for zimfarm notification processor.

Tests the complete processing flow from notification ingestion through book
and title association, verifying observable final states rather than
implementation details.
"""

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import (
    Book,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
    ZimfarmNotification,
)
from cms_backend.mill.context import Context as MillContext
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


class TestBadNotifications:
    """Test notifications that fail validation and are marked as bad_notification."""

    def test_missing_mandatory_keys(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """Notification missing article_count and media_count → bad_notification."""
        content = {
            "size": 1000000,
            "metadata": {"Name": "test"},
            "zimcheck": {},
            "folder_name": "test",
            "filename": "test.zim",
        }
        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "bad_notification"
        assert any("missing mandatory keys" in event for event in notification.events)

    def test_invalid_filename_type(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """Notification with filename as int instead of string → bad_notification."""
        content = VALID_NOTIFICATION_CONTENT.copy()
        content["filename"] = 123  # Invalid: should be string

        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "bad_notification"
        assert any(
            "filename must be a non-empty string" in event
            for event in notification.events
        )

    def test_empty_filename(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """Notification with empty filename → bad_notification."""
        content = VALID_NOTIFICATION_CONTENT.copy()
        content["filename"] = ""

        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "bad_notification"

    def test_invalid_folder_name_type(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """Notification with folder_name as None → bad_notification."""
        content = VALID_NOTIFICATION_CONTENT.copy()
        content["folder_name"] = None  # pyright: ignore[reportArgumentType]

        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "bad_notification"
        assert any(
            "folder_name must be a string" in event for event in notification.events
        )


class TestValidNotificationNoMatchingTitle:
    """Test valid notifications when no matching title exists in the system."""

    def test_creates_book_in_quarantine(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """Valid notification, no matching title → book created in quarantine."""
        notification = create_zimfarm_notification(content=VALID_NOTIFICATION_CONTENT)
        dbsession.flush()

        process_notification(dbsession, notification)

        # Verify notification marked as processed
        assert notification.status == "processed"

        # Verify book was created
        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.article_count == VALID_NOTIFICATION_CONTENT["article_count"]
        assert book.media_count == VALID_NOTIFICATION_CONTENT["media_count"]
        assert book.size == VALID_NOTIFICATION_CONTENT["size"]

        # Verify book has location in quarantine
        assert len(book.locations) == 1
        location = book.locations[0]
        assert location.filename == VALID_NOTIFICATION_CONTENT["filename"]
        assert location.status == "current"

        # Verify book is not in error state (waiting passively for title)
        assert book.has_error is False
        assert book.location_kind == "quarantine"
        assert book.needs_processing is False
        assert book.needs_file_operation is False

    def test_creates_book_with_empty_folder_name(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """
        Valid notification with empty folder_name (file at quarantine root) →
        book created.
        """
        content = VALID_NOTIFICATION_CONTENT.copy()
        content["folder_name"] = ""

        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        # Verify notification marked as processed
        assert notification.status == "processed"

        # Verify book was created
        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.article_count == VALID_NOTIFICATION_CONTENT["article_count"]
        assert book.media_count == VALID_NOTIFICATION_CONTENT["media_count"]
        assert book.size == VALID_NOTIFICATION_CONTENT["size"]

        # Verify book has location in quarantine at root (quarantine_base_path with
        # empty folder)
        assert len(book.locations) == 1
        location = book.locations[0]
        assert location.filename == VALID_NOTIFICATION_CONTENT["filename"]
        assert location.status == "current"
        assert location.path == MillContext.quarantine_base_path

        # Verify book is not in error state
        assert book.has_error is False
        assert book.location_kind == "quarantine"
        assert book.needs_processing is False
        assert book.needs_file_operation is False


class TestValidNotificationMissingZimMetadata:
    """Test valid notifications where book metadata is incomplete."""

    def test_missing_metadata_sets_error_flag(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """Valid notification but missing ZIM metadata → book marked with error."""
        # Create notification with valid structure but missing metadata field
        content = VALID_NOTIFICATION_CONTENT.copy()
        content["metadata"] = {
            "Name": "test_en_all",
            # Missing Title, Creator, Publisher, Date, Description, Language
        }

        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        # Notification still processed
        assert notification.status == "processed"

        # But book has error flag
        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.location_kind == "quarantine"
        assert book.has_error is True
        assert any("missing mandatory metadata" in event for event in book.events)
        assert book.needs_processing is False
        assert book.needs_file_operation is False


class TestValidNotificationWithMatchingTitleDevMaturity:
    """Test valid notifications that match an existing title with dev maturity.

    Dev maturity titles should have their books moved to staging.
    """

    def test_moves_book_to_staging(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
    ):
        """Valid notification + matching dev maturity title → book moves to staging."""
        # Create title that matches book name
        title = create_title(name="test_en_all")
        title.maturity = "dev"
        dbsession.flush()

        notification = create_zimfarm_notification(content=VALID_NOTIFICATION_CONTENT)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "processed"

        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.title_id == title.id

        current_locations = [loc for loc in book.locations if loc.status == "current"]
        assert len(current_locations) == 1
        assert current_locations[0].warehouse_id == MillContext.quarantine_warehouse_id
        assert current_locations[0].path == MillContext.quarantine_base_path / str(
            VALID_NOTIFICATION_CONTENT["folder_name"]
        )

        target_locations = [loc for loc in book.locations if loc.status == "target"]
        assert len(target_locations) == 1
        assert target_locations[0].warehouse_id == MillContext.staging_warehouse_id
        assert target_locations[0].path == MillContext.staging_base_path

        assert book.location_kind == "staging"
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False

    def test_moves_book_to_staging_with_empty_folder_name(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
    ):
        """
        Valid notification with empty folder_name + dev maturity title → book
        moves to staging.
        """
        # Create title that matches book name
        title = create_title(name="test_en_all")
        title.maturity = "dev"
        dbsession.flush()

        content = VALID_NOTIFICATION_CONTENT.copy()
        content["folder_name"] = ""

        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "processed"

        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.title_id == title.id

        current_locations = [loc for loc in book.locations if loc.status == "current"]
        assert len(current_locations) == 1
        assert current_locations[0].warehouse_id == MillContext.quarantine_warehouse_id
        assert current_locations[0].path == MillContext.quarantine_base_path

        target_locations = [loc for loc in book.locations if loc.status == "target"]
        assert len(target_locations) == 1
        assert target_locations[0].warehouse_id == MillContext.staging_warehouse_id
        assert target_locations[0].path == MillContext.staging_base_path

        assert book.location_kind == "staging"
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False


class TestValidNotificationWithMatchingTitleRobustMaturity:
    """Test valid notifications that match a robust maturity title.

    Robust maturity titles have their books moved directly to production collections.
    """

    def test_moves_book_to_collection_warehouses(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        create_collection: Callable[..., Collection],
        create_warehouse: Callable[..., Warehouse],
    ):
        """Valid notification + robust title → book has collection warehouse targets."""

        title = create_title(name="test_en_all")
        title.maturity = "robust"

        prod = create_warehouse(
            name="prod", warehouse_id=UUID("00000000-0000-0000-0000-000000000003")
        )
        collection = create_collection(warehouse=prod)

        ct = CollectionTitle(path=Path("wikipedia"))
        ct.title = title
        ct.collection = collection
        dbsession.add(ct)
        dbsession.flush()

        notification = create_zimfarm_notification(content=VALID_NOTIFICATION_CONTENT)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "processed"

        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.title_id == title.id

        current_locations = [loc for loc in book.locations if loc.status == "current"]
        assert len(current_locations) == 1
        assert current_locations[0].warehouse_id == MillContext.quarantine_warehouse_id
        assert current_locations[0].path == MillContext.quarantine_base_path / str(
            VALID_NOTIFICATION_CONTENT["folder_name"]
        )

        target_locations = [loc for loc in book.locations if loc.status == "target"]
        assert len(target_locations) == 1
        assert target_locations[0].warehouse_id == prod.id
        assert target_locations[0].path == ct.path

        assert book.location_kind == "prod"
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False

    def test_moves_book_to_collection_warehouses_with_empty_folder_name(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        create_collection: Callable[..., Collection],
        create_warehouse: Callable[..., Warehouse],
    ):
        """
        Valid notification with empty folder_name + robust title → book has collection
        warehouse targets.
        """

        title = create_title(name="test_en_all")
        title.maturity = "robust"

        prod = create_warehouse(
            name="prod", warehouse_id=UUID("00000000-0000-0000-0000-000000000003")
        )
        collection = create_collection(warehouse=prod)

        ct = CollectionTitle(path=Path("wikipedia"))
        ct.title = title
        ct.collection = collection
        dbsession.add(ct)
        dbsession.flush()

        content = VALID_NOTIFICATION_CONTENT.copy()
        content["folder_name"] = ""

        notification = create_zimfarm_notification(content=content)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "processed"

        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.title_id == title.id

        current_locations = [loc for loc in book.locations if loc.status == "current"]
        assert len(current_locations) == 1
        assert current_locations[0].warehouse_id == MillContext.quarantine_warehouse_id
        assert current_locations[0].path == MillContext.quarantine_base_path

        target_locations = [loc for loc in book.locations if loc.status == "target"]
        assert len(target_locations) == 1
        assert target_locations[0].warehouse_id == prod.id
        assert target_locations[0].path == ct.path

        assert book.location_kind == "prod"
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False
