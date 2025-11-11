"""Integration tests for book location workflow."""

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import (
    Book,
    BookLocation,
    Title,
    Warehouse,
    WarehousePath,
    ZimfarmNotification,
)
from cms_backend.processors.zimfarm_notification import process_notification

GOOD_ZIM_METADATA = {
    "Name": "test_en_all",
    "Title": "Test Title",
    "Creator": "Test",
    "Publisher": "Test",
    "Date": "2024-01-15",
    "Description": "Test Description",
    "Language": "eng",
    "Flavour": None,
}

GOOD_PRODUCER = {
    "displayName": "farm.openzim.org: test_en_all",
    "displayUrl": "https://farm.openzim.org/recipes/test_en_all",
    "uniqueId": "550e8400-e29b-41d4-a716-446655440000",
}


@pytest.fixture
def warehouse_setup(
    dbsession: OrmSession,  # noqa: ARG001
    create_warehouse: Callable[..., Warehouse],
    create_warehouse_path: Callable[..., WarehousePath],
) -> dict[str, Any]:
    """Set up warehouse and warehouse paths for testing."""
    dev_warehouse = create_warehouse(name="dev-warehouse")
    prod_warehouse = create_warehouse(name="prod-warehouse")

    dev_path = create_warehouse_path(
        warehouse=dev_warehouse,
        folder_name="dev-zim",
    )
    prod_path = create_warehouse_path(
        warehouse=prod_warehouse,
        folder_name="prod-zim",
    )

    return {
        "dev_warehouse": dev_warehouse,
        "prod_warehouse": prod_warehouse,
        "dev_path": dev_path,
        "prod_path": prod_path,
    }


@pytest.fixture
def good_notification_content(
    warehouse_setup: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any]:
    """Create good notification content with warehouse info."""
    return {
        "article_count": 100,
        "media_count": 50,
        "size": 1024000,
        "metadata": GOOD_ZIM_METADATA,
        "zimcheck": {"status": "pass"},
        "warehouse_name": "dev-warehouse",
        "folder_name": "dev-zim",
        "filename": "test_en_all_2024-01-15.zim",
        "producer": GOOD_PRODUCER,
    }


class TestBookLocationCreation:
    """Test book location creation during notification processing."""

    def test_book_gets_current_location_from_notification(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        good_notification_content: dict[str, Any],
    ):
        """Book created from notification should have current location."""
        notification = create_zimfarm_notification(content=good_notification_content)
        assert notification.status == "pending"

        process_notification(dbsession, notification)

        dbsession.flush()
        assert notification.status == "processed"
        assert notification.book is not None

        book = notification.book
        current_locations = [loc for loc in book.locations if loc.status == "current"]

        assert len(current_locations) == 1
        assert current_locations[0].filename == "test_en_all_2024-01-15.zim"
        assert current_locations[0].warehouse_path.warehouse.name == "dev-warehouse"
        assert current_locations[0].warehouse_path.folder_name == "dev-zim"

    def test_notification_without_warehouse_path_fails(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
    ):
        """Notification with non-existent warehouse path should fail."""
        bad_content = {
            "article_count": 100,
            "media_count": 50,
            "size": 1024000,
            "metadata": GOOD_ZIM_METADATA,
            "zimcheck": {"status": "pass"},
            "warehouse_name": "non-existent-warehouse",
            "folder_name": "non-existent-folder",
            "filename": "test.zim",
            "producer": GOOD_PRODUCER,
        }
        notification = create_zimfarm_notification(content=bad_content)

        process_notification(dbsession, notification)

        dbsession.flush()
        assert notification.status == "bad_notification"
        assert any("warehouse path not found" in event for event in notification.events)


class TestTargetLocationCreation:
    """Test target location creation when book is added to title."""

    def test_target_locations_created_for_dev_title(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
        good_notification_content: dict[str, Any],
    ):
        """When book is added to dev title, target locations should use dev paths."""
        dev_path = warehouse_setup["dev_path"]

        # Create dev title
        create_title(
            name="test_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        notification = create_zimfarm_notification(content=good_notification_content)
        process_notification(dbsession, notification)

        dbsession.flush()
        assert notification.book is not None

        book = notification.book
        target_locations = [loc for loc in book.locations if loc.status == "target"]

        assert len(target_locations) == 1
        assert target_locations[0].warehouse_path_id == dev_path.id
        # Target filename should be computed
        assert "2024-01" in target_locations[0].filename
        assert target_locations[0].filename.endswith(".zim")

    def test_target_locations_created_for_prod_title(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
        good_notification_content: dict[str, Any],
    ):
        """When book is added to prod title, target locations should use prod paths."""
        prod_path = warehouse_setup["prod_path"]

        # Create prod title
        create_title(
            name="test_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[],
            prod_warehouse_path_ids=[prod_path.id],
            in_prod=True,
        )

        notification = create_zimfarm_notification(content=good_notification_content)
        process_notification(dbsession, notification)

        dbsession.flush()
        assert notification.book is not None

        book = notification.book
        target_locations = [loc for loc in book.locations if loc.status == "target"]

        assert len(target_locations) == 1
        assert target_locations[0].warehouse_path_id == prod_path.id

    def test_multiple_target_locations_for_multiple_paths(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
        create_warehouse_path: Callable[..., WarehousePath],
        good_notification_content: dict[str, Any],
    ):
        """Title with multiple warehouse paths

        This should create multiple target locations.
        """
        dev_path_1 = warehouse_setup["dev_path"]
        dev_path_2 = create_warehouse_path(
            warehouse=warehouse_setup["dev_warehouse"],
            folder_name="dev-zim-backup",
        )

        # Create title with multiple dev paths
        create_title(
            name="test_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path_1.id, dev_path_2.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        notification = create_zimfarm_notification(content=good_notification_content)
        process_notification(dbsession, notification)

        dbsession.flush()
        assert notification.book is not None

        book = notification.book
        target_locations = [loc for loc in book.locations if loc.status == "target"]

        assert len(target_locations) == 2
        target_warehouse_path_ids = {loc.warehouse_path_id for loc in target_locations}
        assert target_warehouse_path_ids == {dev_path_1.id, dev_path_2.id}


class TestTargetFilenameComputation:
    """Test that target filenames are computed correctly."""

    def test_target_filename_basic_format(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
        good_notification_content: dict[str, Any],
    ):
        """Target filename should follow pattern {name}_{period}.zim."""
        dev_path = warehouse_setup["dev_path"]

        create_title(
            name="test_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        notification = create_zimfarm_notification(content=good_notification_content)
        process_notification(dbsession, notification)

        dbsession.flush()

        assert notification.book

        target_locations = [
            loc for loc in notification.book.locations if loc.status == "target"
        ]

        assert len(target_locations) == 1
        # Should match pattern: test_en_all_2024-01.zim
        assert target_locations[0].filename == "test_en_all_2024-01.zim"

    def test_target_filename_with_flavour(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
    ):
        """Target filename should include flavour if present."""
        dev_path = warehouse_setup["dev_path"]

        metadata_with_flavour = {
            "Name": "wikipedia_en_all",
            "Title": "Wikipedia EN All",
            "Creator": "Test",
            "Publisher": "Test",
            "Date": "2024-02-20",
            "Description": "Test Description",
            "Language": "eng",
            "Flavour": "maxi",
        }

        content = {
            "article_count": 100,
            "media_count": 50,
            "size": 1024000,
            "metadata": metadata_with_flavour,
            "zimcheck": {"status": "pass"},
            "warehouse_name": "dev-warehouse",
            "folder_name": "dev-zim",
            "filename": "wikipedia_en_all_maxi_2024-02-20.zim",
            "producer": GOOD_PRODUCER,
        }

        create_title(
            name="wikipedia_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        notification = create_zimfarm_notification(content=content)
        process_notification(dbsession, notification)

        dbsession.flush()

        assert notification.book

        target_locations = [
            loc for loc in notification.book.locations if loc.status == "target"
        ]

        assert len(target_locations) == 1
        assert target_locations[0].filename == "wikipedia_en_all_maxi_2024-02.zim"

    def test_target_filename_collision_handling(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_book_location: Callable[..., BookLocation],
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
        good_notification_content: dict[str, Any],
    ):
        """Target filename should get suffix if collision exists."""
        dev_path = warehouse_setup["dev_path"]

        create_title(
            name="test_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        # Create existing book with target location to cause collision
        existing_book = create_book(
            name="test_en_all",
            date="2024-01-10",
            flavour=None,
        )
        create_book_location(
            book=existing_book,
            warehouse_path=dev_path,
            filename="test_en_all_2024-01.zim",
            status="target",
        )

        # Process new notification for same period
        notification = create_zimfarm_notification(content=good_notification_content)
        process_notification(dbsession, notification)

        dbsession.flush()

        assert notification.book

        target_locations = [
            loc for loc in notification.book.locations if loc.status == "target"
        ]

        assert len(target_locations) == 1
        # Should get letter suffix to avoid collision
        assert target_locations[0].filename == "test_en_all_2024-01a.zim"


class TestTargetLocationOptimization:
    """Test that target locations are skipped when they match current locations."""

    def test_no_target_when_current_matches_single_path(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_book_location: Callable[..., BookLocation],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
    ):
        """When book current location exactly matches target, no target should
        be created."""
        dev_path = warehouse_setup["dev_path"]

        # Create a book manually with a current location that will match the computed
        # target
        book = create_book(
            name="wikipedia_fr_all",
            date="2024-02-15",
            flavour=None,
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
        )

        # Add current location with target-style filename
        create_book_location(
            book=book,
            warehouse_path=dev_path,
            filename="wikipedia_fr_all_2024-02.zim",
            status="current",
        )

        # Create title with same warehouse path
        title = create_title(
            name="wikipedia_fr_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        dbsession.flush()

        # Add book to title - should skip target creation
        from cms_backend.processors.title import add_book_to_title

        add_book_to_title(dbsession, book, title)
        dbsession.flush()

        current_locations = [loc for loc in book.locations if loc.status == "current"]
        target_locations = [loc for loc in book.locations if loc.status == "target"]

        # Should have current location
        assert len(current_locations) == 1
        assert current_locations[0].warehouse_path_id == dev_path.id
        assert current_locations[0].filename == "wikipedia_fr_all_2024-02.zim"

        # Should NOT have target location (optimization applied)
        assert len(target_locations) == 0

        # Check event log
        assert any(
            "book already at all target locations" in event for event in book.events
        )

    def test_no_target_when_current_matches_multiple_paths(
        self,
        dbsession: OrmSession,
        create_book: Callable[..., Book],
        create_title: Callable[..., Title],
        create_book_location: Callable[..., BookLocation],
        warehouse_setup: dict[str, Any],
        create_warehouse_path: Callable[..., WarehousePath],
    ):
        dev_path_1 = warehouse_setup["dev_path"]
        dev_path_2 = create_warehouse_path(
            warehouse=warehouse_setup["dev_warehouse"],
            folder_name="dev-zim-backup",
        )

        # Create a book with current locations at both paths
        book = create_book(
            name="wiktionary_es_all",
            date="2024-03-10",
            flavour="maxi",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
        )

        # Add current locations at both paths with target-style filename
        create_book_location(
            book=book,
            warehouse_path=dev_path_1,
            filename="wiktionary_es_all_maxi_2024-03.zim",
            status="current",
        )
        create_book_location(
            book=book,
            warehouse_path=dev_path_2,
            filename="wiktionary_es_all_maxi_2024-03.zim",
            status="current",
        )

        # Create title with multiple dev paths
        title = create_title(
            name="wiktionary_es_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path_1.id, dev_path_2.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        dbsession.flush()

        # Add book to title - should skip target creation
        from cms_backend.processors.title import add_book_to_title

        add_book_to_title(dbsession, book, title)
        dbsession.flush()

        current_locations = [loc for loc in book.locations if loc.status == "current"]
        target_locations = [loc for loc in book.locations if loc.status == "target"]

        # Should have 2 current locations
        assert len(current_locations) == 2
        current_path_ids = {loc.warehouse_path_id for loc in current_locations}
        assert current_path_ids == {dev_path_1.id, dev_path_2.id}

        # Should NOT have target locations (optimization applied)
        assert len(target_locations) == 0

        # Check event log
        assert any(
            "book already at all target locations" in event for event in book.events
        )

    def test_target_created_when_partial_match(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
        create_warehouse_path: Callable[..., WarehousePath],
        good_notification_content: dict[str, Any],
    ):
        """When book only matches some target paths, all targets should be created."""
        dev_path_1 = warehouse_setup["dev_path"]
        dev_path_2 = create_warehouse_path(
            warehouse=warehouse_setup["dev_warehouse"],
            folder_name="dev-zim-backup",
        )

        # Adjust filename to match computed target
        good_notification_content["filename"] = "test_en_all_2024-01.zim"

        # Create title with multiple dev paths
        create_title(
            name="test_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path_1.id, dev_path_2.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        notification = create_zimfarm_notification(content=good_notification_content)
        process_notification(dbsession, notification)

        dbsession.flush()
        assert notification.book is not None

        book = notification.book
        current_locations = [loc for loc in book.locations if loc.status == "current"]
        target_locations = [loc for loc in book.locations if loc.status == "target"]

        # Should have 1 current location
        assert len(current_locations) == 1
        assert current_locations[0].warehouse_path_id == dev_path_1.id

        # Should have 2 target locations (NO optimization, partial match)
        assert len(target_locations) == 2
        target_path_ids = {loc.warehouse_path_id for loc in target_locations}
        assert target_path_ids == {dev_path_1.id, dev_path_2.id}

        # Check event log - should NOT have optimization message
        assert not any(
            "book already at all target locations" in event for event in book.events
        )

    def test_target_created_when_filename_differs(
        self,
        dbsession: OrmSession,
        create_zimfarm_notification: Callable[..., ZimfarmNotification],
        create_title: Callable[..., Title],
        warehouse_setup: dict[str, Any],
        good_notification_content: dict[str, Any],
    ):
        """When book filename differs from computed target, target should be created."""
        dev_path = warehouse_setup["dev_path"]

        # Keep original filename that differs from computed target
        # Original: test_en_all_2024-01-15.zim
        # Computed target: test_en_all_2024-01.zim

        create_title(
            name="test_en_all",
            producer_unique_id=GOOD_PRODUCER["uniqueId"],
            dev_warehouse_path_ids=[dev_path.id],
            prod_warehouse_path_ids=[],
            in_prod=False,
        )

        notification = create_zimfarm_notification(content=good_notification_content)
        process_notification(dbsession, notification)

        dbsession.flush()
        assert notification.book is not None

        book = notification.book
        current_locations = [loc for loc in book.locations if loc.status == "current"]
        target_locations = [loc for loc in book.locations if loc.status == "target"]

        # Should have current location with original filename
        assert len(current_locations) == 1
        assert current_locations[0].filename == "test_en_all_2024-01-15.zim"

        # Should have target location with computed filename (NO optimization)
        assert len(target_locations) == 1
        assert target_locations[0].filename == "test_en_all_2024-01.zim"

        # Check event log - should NOT have optimization message
        assert not any(
            "book already at all target locations" in event for event in book.events
        )
