import datetime
import re
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.context import Context
from cms_backend.db.book import (
    backup_book,
    get_book_history,
    get_book_history_entry_or_none,
    get_book_metadata_issues,
    get_differing_metadata_keys,
    get_zimcheck_errors,
    recover_book,
    remove_book_backup,
    revert_book,
    update_book,
    update_book_issues,
)
from cms_backend.db.book import create_book as db_create_book
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Account,
    Book,
    BookLocation,
    Collection,
    Title,
    Warehouse,
    ZimfarmNotification,
)
from cms_backend.db.rules import has_flavour_mismatch
from cms_backend.schemas.models import BookUpdateSchema
from cms_backend.utils.datetime import getnow


def test_create_book(
    dbsession: OrmSession,
    zimfarm_notification: ZimfarmNotification,
    faker: Faker,
    account: Account,
):
    """Create a book from a zimfarm notification"""
    book_id = zimfarm_notification.id  # Use zimfarm notification ID as book ID
    book = db_create_book(
        dbsession,
        author_id=account.id,
        book_id=book_id,
        article_count=faker.random_int(),
        media_count=faker.random_int(),
        size=faker.random_int(),
        zim_metadata={"key": "value"},
        zimcheck_result_url="https://www.example.com/zimcheck.json",
        zimfarm_notification=zimfarm_notification,
    )
    dbsession.flush()
    assert book.zimfarm_notification == zimfarm_notification
    assert zimfarm_notification.book_id == book.id
    assert zimfarm_notification.book == book
    assert any(
        event
        for event in zimfarm_notification.events
        if "notification transformed into book" in event
    )
    assert any(
        event for event in book.events if "created from Zimfarm notification" in event
    )


def test_get_differing_metadata_keys(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    illustration_48x48_at_1: str,
):
    """Get the different metadata keys between book and it's title."""
    title = create_title(
        title="Title",
        creator="Title Creator",
        publisher="openZIM",
        description="Title Description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )

    book = create_book(
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        }
    )
    book.title_id = title.id
    dbsession.add(book)
    dbsession.flush()

    differences = get_differing_metadata_keys(book)
    assert set(differences) == {"Title", "Creator", "Publisher", "Description"}


def test_update_deleted_book(
    dbsession: OrmSession, account: Account, create_book: Callable[..., Book]
):
    book = create_book(location_kind="deleted")
    with pytest.raises(RecordDoesNotExistError, match=r"Book .* is already deleted"):
        update_book(
            dbsession,
            book_id=book.id,
            author_id=account.id,
            payload=BookUpdateSchema(flavour="maxi"),
        )


def test_update_book_belonging_to_archived_title(
    dbsession: OrmSession,
    account: Account,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    book = create_book()
    title = create_title(archived=True)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"Book title .* is currently archived"):
        update_book(
            dbsession,
            author_id=account.id,
            book_id=book.id,
            payload=BookUpdateSchema(flavour="maxi"),
        )


def test_update_book_with_same_flavour(
    dbsession: OrmSession,
    account: Account,
    create_book: Callable[..., Book],
):
    book = create_book(flavour="maxi")
    assert book.flavour is not None
    assert len(book.history_entries) == 1
    update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(flavour=book.flavour),
    )
    assert len(book.history_entries) == 1


def test_update_book_with_different_flavour(
    dbsession: OrmSession,
    account: Account,
    create_book: Callable[..., Book],
):
    book = create_book(flavour="maxi")
    assert book.flavour is not None
    assert len(book.history_entries) == 1
    book = update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(flavour="mini"),
    )
    assert book.flavour == "mini"
    assert len(book.history_entries) == 2


@pytest.mark.parametrize(
    "skip, limit, expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 2, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 10, 6, id="first-page-with-high-limit"),
    ],
)
def test_get_book_history(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving book history with pagination"""
    book = create_book(name="test_book", flavour="maxi")
    for i in range(5):
        update_book(
            dbsession,
            book_id=book.id,
            author_id=account.id,
            payload=BookUpdateSchema(
                flavour=f"mini_{i}",
                comment=f"Update {i}",
            ),
        )
    results = get_book_history(
        dbsession,
        book_id=book.id,
        skip=skip,
        limit=limit,
    )
    assert results.nb_records == 6
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_get_book_history_entry_or_none(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    account: Account,
):
    """Test retrieving a specific book history entry"""
    book = create_book(name="test_book", flavour="maxi")

    update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(
            flavour="mini",
            comment="Initial version",
        ),
    )

    history_result = get_book_history(dbsession, book_id=book.id, skip=0, limit=1)
    history_id = history_result.records[0].id

    history_entry = get_book_history_entry_or_none(
        dbsession, book_id=book.id, history_id=history_id
    )
    assert history_entry is not None
    assert history_entry.flavour == "mini"
    assert history_entry.comment == "Initial version"


def test_revert_book(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    account: Account,
):
    """Test reverting a book to a previous state"""
    book = create_book(name="test_book", flavour="maxi")

    # Create a first history entry
    update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(
            flavour="mini",
            comment="First version",
        ),
    )

    history_result = get_book_history(dbsession, book_id=book.id, skip=0, limit=1)
    first_history_id = history_result.records[0].id

    # Make a second update with different flavour
    book = update_book(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        payload=BookUpdateSchema(
            flavour="nopic",
            comment="Second version",
        ),
    )

    assert book.flavour == "nopic"

    # Revert to the first version
    reverted_book = revert_book(
        dbsession,
        book_id=book.id,
        history_id=first_history_id,
        author_id=account.id,
        comment="Reverting to version 1",
    )
    assert reverted_book.flavour == "mini"


@patch("cms_backend.db.book.get_zimcheck_errors")
def test_update_book_flavour_mismatch_issues(
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    account: Account,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    """
    Test that book with  a flavour mismatch between it and it's title has
    it's issues reset when it's flavour is updated to the same as the title
    """
    mock_get_zimcheck_errors.return_value = []
    content = {
        "Name": "test_en_all",
        "Title": "Test Article",
        "Creator": "Test Creator",
        "Publisher": "Test Publisher",
        "Date": "2025-01-01",
        "Description": "Test description",
        "Language": "eng",
        "Illustration_48x48@1": (
            "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAOklEQVR4nO3OwQkAIAwA"
            "wfRf2u1gB4kfQeYKCHcNAAAAAAAAAAAAgL96bPf7EgAAAAAAAIC/egF5uwED0gQ8ugAAAA"
            "BJRU5ErkJggg=="
        ),
    }

    title = create_title(
        name="test_en_all",
        flavours=["maxi", "mini"],
        title=content["Title"],
        creator=content["Creator"],
        publisher=content["Publisher"],
        description=content["Description"],
        language=content["Language"],
        illustration_48x48_at_1=content["Illustration_48x48@1"],
    )
    book = create_book(zim_metadata=content)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    book = update_book(
        dbsession,
        author_id=account.id,
        book_id=book.id,
        payload=BookUpdateSchema(flavour="nopic"),
    )
    assert len(book.issues) == 1
    assert book.issues == ["flavour mismatch"]

    book = update_book(
        dbsession,
        author_id=account.id,
        book_id=book.id,
        payload=BookUpdateSchema(flavour="maxi"),
    )
    assert len(book.issues) == 0


@pytest.mark.parametrize(
    "book_flavour, title_flavours, expected",
    [
        pytest.param(None, ["maxi"], True),
        pytest.param("maxi", ["maxi", "mini"], False),
        pytest.param("maxi", ["mini", "nopic"], True),
        pytest.param(None, [], False),
        pytest.param("maxi", [], True),
        pytest.param("", [], False),
        pytest.param("", ["maxi"], True),
    ],
)
def test_has_flavour_mismatch(
    book_flavour: str, title_flavours: list[str], *, expected: bool
):
    assert has_flavour_mismatch(book_flavour, title_flavours) is expected


def test_backup_book_success(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    monkeypatch: pytest.MonkeyPatch,
):
    """Test successfully backing up a book."""
    backup_warehouse = create_warehouse()
    monkeypatch.setattr(Context, "backup_warehouse_id", backup_warehouse.id)
    monkeypatch.setattr(Context, "backup_base_path", Path("backup"))

    warehouse = create_warehouse()
    title = create_title()
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    book = backup_book(dbsession, book_id=book.id)

    # Verify backup has a current location (source) and target location
    current_locations = [loc for loc in book.locations if loc.status == "current"]
    target_locations = [loc for loc in book.locations if loc.status == "target"]
    backup_target_locations = [
        loc for loc in book.locations if loc.status == "target" and loc.is_backup
    ]
    assert len(current_locations) == 1
    assert len(target_locations) == 2
    assert len(backup_target_locations) == 1
    assert current_locations[0].warehouse_id == warehouse.id
    assert backup_target_locations[0].warehouse_id == backup_warehouse.id
    assert book.needs_file_operation is True


def test_backup_book_already_has_backup_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that backing up a book that already has a backup raises an error."""
    warehouse = create_warehouse()
    title = create_title()
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
        is_backup=True,
    )
    dbsession.flush()

    with pytest.raises(ValueError, match="Book already has a backup"):
        backup_book(dbsession, book_id=book.id)


def test_backup_book_no_title_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that backing up a book without a title raises an error."""
    warehouse = create_warehouse()
    book = create_book(name="test_en_all", date="2024-01")
    book.title = None
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    with pytest.raises(ValueError, match="Book has no associated title"):
        backup_book(dbsession, book_id=book.id)


def test_backup_book_archived_title_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that backing up a book with archived title raises an error."""
    warehouse = create_warehouse()
    title = create_title(archived=True)  # Archived title
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    with pytest.raises(
        ValueError, match=f"Book title {book.title_id} is currently archived"
    ):
        backup_book(dbsession, book_id=book.id)


def test_backup_book_no_current_location_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
):
    """Test that backing up a book without current location raises an error."""
    title = create_title()
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    dbsession.flush()

    with pytest.raises(ValueError, match=f"Book {book.id} has no current location"):
        backup_book(dbsession, book_id=book.id)


def test_remove_book_backup_no_existing_backup_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that removing backup for a book with no existing backups raises error"""
    warehouse = create_warehouse()
    title = create_title()
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    dbsession.flush()

    with pytest.raises(ValueError, match="Book does not have a backup"):
        remove_book_backup(dbsession, book_id=book.id)


def test_backup_locations_is_backup_property_removed(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_collection: Callable[..., Collection],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that removing backups for a book removes the is_backup property for existing
    backups
    """
    warehouse = create_warehouse()
    title = create_title()
    create_collection(warehouse=warehouse, title_ids_with_paths=[(title.id, "zim")])
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "staging"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    # Create two current locations, one as backup and one a normal location
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("backup"),
        filename="test_en_all_2024-01.zim",
        status="current",
        is_backup=True,
    )
    dbsession.flush()

    book = remove_book_backup(dbsession, book_id=book.id)
    assert book.needs_file_operation is True
    # no more locations have backup property and one new target
    assert (
        len(
            [loc for loc in book.locations if loc.is_backup and loc.status == "current"]
        )
        == 0
    )
    assert len([loc for loc in book.locations if loc.status == "target"]) == 1


def test_remove_backup_for_deleted_book_moves_book_to_deleted(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_book_location: Callable[..., BookLocation],
    create_collection: Callable[..., Collection],
    create_warehouse: Callable[..., Warehouse],
):
    """Test that removing backups for a deleted book moves the book to to_delete"""
    warehouse = create_warehouse()
    title = create_title()
    create_collection(warehouse=warehouse, title_ids_with_paths=[(title.id, "zim")])
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    book.location_kind = "deleted"
    book.has_error = False
    book.needs_processing = False
    book.needs_file_operation = False

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("backup"),
        filename="test_en_all_2024-01.zim",
        status="current",
        is_backup=True,
    )
    dbsession.flush()

    book = remove_book_backup(dbsession, book_id=book.id)
    assert book.needs_file_operation is True
    assert book.location_kind == "to_delete"
    # no more backup locations and backup is now the current location
    assert (
        len(
            [loc for loc in book.locations if loc.is_backup and loc.status == "current"]
        )
        == 0
    )
    assert len([loc for loc in book.locations if loc.status == "target"]) == 0
    assert len([loc for loc in book.locations if loc.status == "current"]) == 1


def test_recover_deleted_book_with_backup(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    monkeypatch: pytest.MonkeyPatch,
):
    """Test recovering a book that is already deleted but has a backup"""
    warehouse = create_warehouse()

    monkeypatch.setattr(Context, "staging_warehouse_id", warehouse.id)
    monkeypatch.setattr(Context, "staging_base_path", Path("staging"))

    title = create_title()
    create_collection(warehouse=warehouse, title_ids_with_paths=[(title.id, "zim")])
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("backup"),
        filename="test_en_all_2024-01.zim",
        status="current",
        is_backup=True,
    )

    now = getnow()
    book.location_kind = "deleted"
    book.needs_file_operation = False
    book.needs_processing = False
    book.deletion_date = now - datetime.timedelta(days=1)
    dbsession.flush()

    book = recover_book(dbsession, book_id=book.id)

    assert book.location_kind != "deleted"
    assert book.needs_file_operation is True
    assert book.deletion_date is None
    assert "Book restored from 'deleted'" in book.events[-1]
    # book now has two target locations and one current location
    assert len([loc for loc in book.locations if loc.status == "current"]) == 1
    assert len([loc for loc in book.locations if loc.status == "target"]) == 2


def test_recover_deleted_book_with_no_backup(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_warehouse: Callable[..., Warehouse],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
):
    """Test recovering a book that is already deleted but has a backup"""
    warehouse = create_warehouse()
    title = create_title()
    create_collection(warehouse=warehouse, title_ids_with_paths=[(title.id, "zim")])
    book = create_book(name="test_en_all", date="2024-01")
    book.title = title

    now = getnow()
    book.location_kind = "deleted"
    book.needs_file_operation = False
    book.needs_processing = False
    book.deletion_date = now - datetime.timedelta(days=1)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"Book does not have a backup."):
        recover_book(dbsession, book_id=book.id)


@pytest.mark.parametrize(
    "article_count,media_count,article_count_threshold,media_count_threshold,expected_issues",
    [
        # latest book article_count is 105 and media_count is 100
        # define collection thresholds
        pytest.param(
            105,
            100,
            0.1,
            0.1,
            set(),  # pyright: ignore[reportUnknownArgumentType]
            id="collection-thresholds-within-threshold",
        ),
        pytest.param(
            130,
            105,
            0.1,
            0.1,
            {"article count"},
            id="collection-thresholds-article-count-exceeds-threshold",
        ),
        pytest.param(
            100,
            115,
            0.1,
            0.1,
            {"media count"},
            id="collection-thresholds-media-count-exceeds-threshold",
        ),
        pytest.param(
            130,
            155,
            0.1,
            0.1,
            {"media count", "article count"},
            id="collection-thresholds-media-and-article-count-exceeds-threshold",
        ),
        pytest.param(
            90,
            80,
            0.1,
            0.1,
            {"media count", "article count"},
            id="collection-thresholds-media-and-article-count-below-threshold",
        ),
        # collection has no threshold, so, 100% change is only what triggers issues
        pytest.param(
            105,
            100,
            None,
            None,
            set(),  # pyright: ignore[reportUnknownArgumentType]
            id="no-collection-thresholds-within-threshold",
        ),
        pytest.param(
            211,
            105,
            None,
            None,
            {"article count"},
            id="no-collection-thresholds-article-count-exceeds-threshold",
        ),
        pytest.param(
            100,
            201,
            None,
            None,
            {"media count"},
            id="no-collection-thresholds-media-count-exceeds-threshold",
        ),
        pytest.param(
            211,
            201,
            None,
            None,
            {"media count", "article count"},
            id="no-collection-thresholds-media-and-article-count-exceeds-threshold",
        ),
    ],
)
@patch("cms_backend.db.book.get_zimcheck_errors")
def test_update_book_issues_item_count_issues(
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    article_count: int,
    media_count: int,
    article_count_threshold: float,
    media_count_threshold: float,
    expected_issues: set[str],
):
    """Test that update_book_issues correctly flags issues with book item count"""
    mock_get_zimcheck_errors.return_value = []
    warehouse = create_warehouse()
    content = {
        "Name": "test_en_all",
        "Title": "Test Article",
        "Creator": "Test Creator",
        "Publisher": "Test Publisher",
        "Date": "2025-01-01",
        "Description": "Test description",
        "Language": "eng",
        "Illustration_48x48@1": (
            "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAOklEQVR4nO3OwQkAIAwA"
            "wfRf2u1gB4kfQeYKCHcNAAAAAAAAAAAAgL96bPf7EgAAAAAAAIC/egF5uwED0gQ8ugAAAA"
            "BJRU5ErkJggg=="
        ),
    }
    title = create_title(
        name="test_en_all",
        flavours=["maxi", "mini"],
        title=content["Title"],
        creator=content["Creator"],
        publisher=content["Publisher"],
        description=content["Description"],
        language=content["Language"],
        illustration_48x48_at_1=content["Illustration_48x48@1"],
    )
    # create a collection that tolerates only 10% increase in media and article count
    create_collection(
        warehouse=warehouse,
        title_ids_with_paths=[(title.id, "zim")],
        media_count_change_threshold=media_count_threshold,
        article_count_change_threshold=article_count_threshold,
    )

    # create the latest book with media_count of 100 and article count of 105
    latest_book = create_book(
        article_count=105,
        media_count=100,
        flavour="maxi",
        title_id=title.id,
        zim_metadata=content,
        location_kind="prod",
    )

    create_book_location(
        book=latest_book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    book = create_book(
        article_count=article_count,
        media_count=media_count,
        flavour="maxi",
        title_id=title.id,
        zim_metadata=content,
    )
    dbsession.flush()
    update_book_issues(dbsession, book)
    assert set(book.issues) == expected_issues


@pytest.mark.parametrize(
    "title,description,flavour,name,event_regex,expected",
    [
        pytest.param(
            "é" * 31,
            "é" * 40,
            "",
            "test_en_all",
            r"book Title metadata is \d+ characters long",
            True,
            id="title-too-long",
        ),
        pytest.param(
            "é" * 30,
            "é" * 90,
            "",
            "test_en_all",
            r"book Description metadata is \d+ characters long",
            True,
            id="description-too-long",
        ),
        pytest.param(
            "é" * 30,
            "é" * 80,
            "_maxi",
            "test_en_all",
            "book Flavour metadata .* contains non-alphabetic characters",
            True,
            id="invalid-flavour",
        ),
        pytest.param(
            "é" * 30,
            "é" * 80,
            "maxi",
            "test_en_all",
            "",
            False,
            id="all-good",
        ),
    ],
)
def test_book_has_bad_metadata(
    create_book: Callable[..., Book],
    title: str,
    description: str,
    flavour: str | None,
    name: str,
    event_regex: str,
    *,
    expected: bool,
):
    book = create_book(
        zim_metadata={
            "Name": name,
            "Title": title,
            "Description": description,
            "Flavour": flavour,
        }
    )
    issues = get_book_metadata_issues(book)
    assert bool(issues) is expected
    if expected:
        assert any(re.search(event_regex, issue) for issue in issues)


@pytest.mark.parametrize(
    "ignore_scraper,passes_quality_check",
    [
        (True, True),
        (False, False),
    ],
)
def test_get_zimcheck_errors_ignore_scraper(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    monkeypatch: pytest.MonkeyPatch,
    *,
    ignore_scraper: bool,
    passes_quality_check: bool,
):
    """Test conditional scraper ignore with zimcheck errors"""
    book = create_book()
    book.zim_metadata["Scraper"] = "mwoffliner 1.75"
    book.zimcheck_summary = {
        "zimcheck_version": "1.0.0",
        "status": False,
        "checks": ["internal_urls"],
        "error_count": 1,
        "warning_count": 1,
        "retcode": 1,
    }
    dbsession.add(book)
    dbsession.flush()
    if ignore_scraper:
        monkeypatch.setattr(
            "cms_backend.context.Context.zimcheck_scrapers_whitelist_regex",
            re.compile(r"mwoffliner.*|sotoki"),
        )
    errors = get_zimcheck_errors(book)
    if passes_quality_check:
        assert len(errors) == 0
    else:
        assert len(errors) > 0
