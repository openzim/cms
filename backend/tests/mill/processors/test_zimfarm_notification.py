"""Integration tests for zimfarm notification processor.

Tests the complete processing flow from notification ingestion through book
and title association, verifying observable final states rather than
implementation details.
"""

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db.models import (
    Book,
    Collection,
    CollectionTitle,
    Title,
    Warehouse,
    ZimfarmNotification,
)
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
        "Illustration_48x48@1": "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",  # noqa: E501
    },
    "zimcheck_url": "https://www.example.com/zimcheck.json",
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
            "zimcheck_url": "https://www.example.com/zimcheck.json",
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
        warehouse: Warehouse,  # noqa: ARG002
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
        warehouse: Warehouse,  # noqa: ARG002
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
        assert location.path == Context.quarantine_base_path

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
        warehouse: Warehouse,  # noqa: ARG002
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


class TestValidNotificationWithMatchingTitleUnstableMaturity:
    """Test valid notifications that match an existing title with unstable maturity.

    Unstable maturity titles should have their books moved to staging.
    """

    def test_set_missing_title_metadata_from_book(
        self,
        dbsession: OrmSession,
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
    ):
        """
        Set title metadata from book because title has no metadata set
        """
        # Create title that matches book name
        title = create_title(name="test_en_all")
        title.maturity = "unstable"
        dbsession.flush()

        notification = create_zimfarm_notification(content=VALID_NOTIFICATION_CONTENT)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "processed"

        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert len(book.issues) == 0
        assert book.title_id == title.id

        dbsession.refresh(title)
        assert title.title == book.zim_metadata["Title"]
        assert title.creator == book.zim_metadata["Creator"]
        assert title.publisher == book.zim_metadata["Publisher"]
        assert title.description == book.zim_metadata["Description"]
        assert title.language == book.zim_metadata["Language"]

    def test_preserve_title_metadata(
        self,
        dbsession: OrmSession,
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        illustration_48x48_at_1: str,
    ):
        """
        Preserve existing title metadata even though book has different metadata
        """
        # Create title that matches book name with all metadata matching with book
        # except for language
        title = create_title(
            name="test_en_all",
            title="Test Article",
            creator="Test Creator",
            publisher="Test Publisher",
            description="Test Description",
            language="ger",
            illustration_48x48_at_1=illustration_48x48_at_1,
        )
        title.maturity = "unstable"
        dbsession.flush()

        notification = create_zimfarm_notification(content=VALID_NOTIFICATION_CONTENT)
        dbsession.flush()

        process_notification(dbsession, notification)

        assert notification.status == "processed"

        book = dbsession.query(Book).filter_by(id=notification.id).first()
        assert book is not None
        assert book.title_id == title.id
        assert len(book.issues) == 1
        assert set(book.issues) == {"metadata mismatch"}

        dbsession.refresh(title)
        assert title.language != book.zim_metadata["Language"]

    def test_moves_book_to_staging(
        self,
        dbsession: OrmSession,
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
    ):
        """
        Valid notification + matching unstable maturity title → book moves to staging.
        """
        # Create title that matches book name
        title = create_title(name="test_en_all")
        title.maturity = "unstable"
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
        assert current_locations[0].warehouse_id == Context.quarantine_warehouse_id
        assert current_locations[0].path == Context.quarantine_base_path / str(
            VALID_NOTIFICATION_CONTENT["folder_name"]
        )

        target_locations = [loc for loc in book.locations if loc.status == "target"]
        assert len(target_locations) == 1
        assert target_locations[0].warehouse_id == Context.staging_warehouse_id
        assert target_locations[0].path == Context.staging_base_path

        assert book.location_kind == "staging"
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False

    def test_moves_book_to_staging_with_empty_folder_name(
        self,
        dbsession: OrmSession,
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
    ):
        """
        Valid notification with empty folder_name + unstable maturity title → book
        moves to staging.
        """
        # Create title that matches book name
        title = create_title(name="test_en_all")
        title.maturity = "unstable"
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
        assert current_locations[0].warehouse_id == Context.quarantine_warehouse_id
        assert current_locations[0].path == Context.quarantine_base_path

        target_locations = [loc for loc in book.locations if loc.status == "target"]
        assert len(target_locations) == 1
        assert target_locations[0].warehouse_id == Context.staging_warehouse_id
        assert target_locations[0].path == Context.staging_base_path

        assert book.location_kind == "staging"
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False


class TestValidNotificationWithMatchingTitleStableMaturity:
    """Test valid notifications that match a stable maturity title.

    Stable maturity titles have their books moved directly to production collections.
    """

    def test_moves_book_to_collection_warehouses(
        self,
        dbsession: OrmSession,
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        create_collection: Callable[..., Collection],
        create_warehouse: Callable[..., Warehouse],
    ):
        """Valid notification + stable title → book has collection warehouse targets."""

        title = create_title(name="test_en_all")
        title.maturity = "stable"

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
        assert current_locations[0].warehouse_id == Context.quarantine_warehouse_id
        assert current_locations[0].path == Context.quarantine_base_path / str(
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
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        create_collection: Callable[..., Collection],
        create_warehouse: Callable[..., Warehouse],
    ):
        """
        Valid notification with empty folder_name + stable title → book has collection
        warehouse targets.
        """

        title = create_title(name="test_en_all")
        title.maturity = "stable"

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
        assert current_locations[0].warehouse_id == Context.quarantine_warehouse_id
        assert current_locations[0].path == Context.quarantine_base_path

        target_locations = [loc for loc in book.locations if loc.status == "target"]
        assert len(target_locations) == 1
        assert target_locations[0].warehouse_id == prod.id
        assert target_locations[0].path == ct.path

        assert book.location_kind == "prod"
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False

    def test_moves_book_to_staging_due_to_diffrent_metadata_from_title(
        self,
        dbsession: OrmSession,
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        create_collection: Callable[..., Collection],
        create_warehouse: Callable[..., Warehouse],
        illustration_48x48_at_1: str,
    ):
        """
        Test that book goes to staging because there is a metadata mismatch between
        it and it's title
        """

        # Create title that matches book name with all metadata matching with book
        # except for language
        title = create_title(
            name="test_en_all",
            title="Test Article",
            creator="Test Creator",
            publisher="Test Publisher",
            description="Test Description",
            language="ger",
            illustration_48x48_at_1=illustration_48x48_at_1,
        )
        title.maturity = "stable"

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
        assert book.location_kind == "staging"
        assert len(book.issues) == 1
        assert set(book.issues) == {"metadata mismatch"}
        assert book.has_error is False
        assert book.needs_file_operation is True
        assert book.needs_processing is False


class TestValidNotificationOnArchivedTitle:
    """Test valid notifications that are associated to an archived title."""

    def test_book_association_with_archived_title(
        self,
        dbsession: OrmSession,
        warehouse: Warehouse,  # noqa: ARG002
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        create_collection: Callable[..., Collection],
        create_warehouse: Callable[..., Warehouse],
    ):
        title = create_title(name="test_en_all", archived=True)
        title.maturity = "stable"

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
        assert book.title_id is None
        assert book.needs_processing is False
        assert any(
            "cannot add book to title because title is archived" in event
            for event in book.events
        )
