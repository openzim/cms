from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.book import book_has_recipe_issue
from cms_backend.db.book_actions import (
    apply_book_promotion_actions,
    get_book_promotion_actions,
)
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import (
    Account,
    Book,
    BookLocation,
    Collection,
    CollectionTitle,
    RequestedTask,
    Title,
    Warehouse,
)
from cms_backend.schemas.models import BaseBookPromotionAction


def test_promotion_actions_book_not_eligible_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """A book with errors or in 'prod' should raise RecordDoesNotExistError."""
    book = create_book(location_kind="prod")

    with pytest.raises(
        RecordDoesNotExistError, match=r"does not meet criteria to be validated"
    ):
        get_book_promotion_actions(dbsession, book_id=book.id)


def test_promotion_actions_missing_metadata_keys_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
):
    """Book missing mandatory ZIM metadata keys should raise ValueError."""
    book = create_book(
        zim_metadata={"Name": "test_en_all"},
        location_kind="quarantine",
    )

    with pytest.raises(ValueError, match=r"missing mandatory metadata keys"):
        get_book_promotion_actions(dbsession, book_id=book.id)


def test_promotion_actions_unsupported_languages(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """
    Book with unsupported language codes produces a whitelist_language_codes  action
    """
    book = create_book(
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "xxx,yyy",  # unsupported codes
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    title = create_title(
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="xxx,yyy",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    lang_actions = [action for action in actions if action.kind == "unknown_languages"]
    assert len(lang_actions) == 1
    assert lang_actions[0].requirement == "information"
    assert lang_actions[0].data == {}
    assert "xxx,yyy" in lang_actions[0].message


def test_promotion_actions_zimcheck_errors(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Book with ZIMcheck errors produces a zimcheck_issues action."""
    monkeypatch.setattr(
        "cms_backend.context.Context.zimcheck_scrapers_whitelist_regex", None
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
        },
        location_kind="quarantine",
    )
    book.zimcheck_summary = {
        "zimcheck_version": "1.0.0",
        "status": False,
        "checks": ["internal_urls"],
        "error_count": 3,
        "warning_count": 1,
        "retcode": 1,
    }
    title = create_title(
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    zimcheck_actions = [
        action for action in actions if action.kind == "zimcheck_issues"
    ]
    assert len(zimcheck_actions) == 1
    assert zimcheck_actions[0].requirement == "information"
    assert zimcheck_actions[0].data == {}
    assert "3" in zimcheck_actions[0].message


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_no_title(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    illustration_48x48_at_1: str,
):
    """Book without a title produces a create_title action"""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
    book = create_book(
        name="test_en_all",
        flavour="maxi",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    assert len(actions) == 1
    assert actions[0].kind == "create_title"
    assert actions[0].requirement == "mandatory"
    assert actions[0].data["name"] == "test_en_all"
    assert actions[0].data["maturity"] == "stable"
    assert len(actions[0].data["flavours"]) != 0
    assert len(actions[0].data["collection_titles"]) == 0


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_no_title_fixed_collection_titles(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    illustration_48x48_at_1: str,
    requested_task: RequestedTask,
):
    """
    Book without a title from a requested task produces a create_title action
    with fixed collection titles
    """
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
    book = create_book(
        name="test_en_all",
        flavour="maxi",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    book.recipe_id = requested_task.recipe_id

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    assert len(actions) == 1
    assert actions[0].kind == "create_title"
    assert actions[0].requirement == "mandatory"
    assert actions[0].data["name"] == "test_en_all"
    assert actions[0].data["maturity"] == "stable"
    assert len(actions[0].data["flavours"]) != 0
    assert len(actions[0].data["collection_titles"]) == 1
    assert (
        actions[0].data["collection_titles"][0]["path"]
        == requested_task.collection_path
    )
    assert (
        actions[0].data["collection_titles"][0]["collection_name"]
        == requested_task.collection.name  # pyright: ignore[reportOptionalMemberAccess]
    )


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_archived_title(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Book with an archived title produces a restore_title action."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
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
        },
        location_kind="quarantine",
    )
    title = create_title(
        name="test_en_all",
        archived=True,
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    restore_actions = [a for a in actions if a.kind == "restore_title"]
    assert len(restore_actions) == 1
    assert restore_actions[0].requirement == "mandatory"
    assert restore_actions[0].data["title_names"] == ["test_en_all"]
    assert "Restore title" in restore_actions[0].message


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_missing_mandatory_title_metadata(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Title missing mandatory metadata produces an update_title_metadata action."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
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
        },
        location_kind="quarantine",
    )
    # Create title with missing illustration (mandatory metadata)
    title = create_title(
        name="test_en_all",
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=None,  # missing
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    metadata_actions = [
        action for action in actions if action.kind == "update_title_metadata"
    ]
    assert len(metadata_actions) == 1
    assert metadata_actions[0].requirement == "optional"
    assert list(metadata_actions[0].data.keys()) == ["illustration_48x48_at_1"]
    assert (
        metadata_actions[0].data["illustration_48x48_at_1"] == illustration_48x48_at_1
    )


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_differing_metadata(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """
    Book with different metadata than its title produces an update_title_metadata
    action.
    """
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
    book = create_book(
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Updated Title",
            "Creator": "Updated Creator",
            "Publisher": "Updated Publisher",
            "Date": "2025-01-01",
            "Description": "Updated description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    title = create_title(
        name="test_en_all",
        title="Old Title",
        creator="Old Creator",
        publisher="Old Publisher",
        description="Old description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    metadata_actions = [a for a in actions if a.kind == "update_title_metadata"]
    assert len(metadata_actions) == 1
    assert metadata_actions[0].data["title"] == "Updated Title"
    assert metadata_actions[0].data["creator"] == "Updated Creator"
    assert metadata_actions[0].data["publisher"] == "Updated Publisher"
    assert metadata_actions[0].data["description"] == "Updated description"


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_maturity_not_stable(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Title with non-stable maturity produces an update_title_maturity action."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
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
        },
        location_kind="quarantine",
    )
    title = create_title(
        name="test_en_all",
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    maturity_actions = [
        action for action in actions if action.kind == "update_title_maturity"
    ]
    assert len(maturity_actions) == 1
    assert maturity_actions[0].requirement == "optional"
    assert maturity_actions[0].data == {"maturity": "stable"}


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_no_collections(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Title without collection entries produces an set_title_collections action."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
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
        },
        location_kind="quarantine",
    )
    title = create_title(
        name="test_en_all",
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    collection_actions = [a for a in actions if a.kind == "set_title_collections"]
    assert len(collection_actions) == 1
    assert collection_actions[0].requirement == "mandatory"
    assert collection_actions[0].data == {"collection_titles": []}


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_flavour_mismatch_no_book_flavour(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """
    Book with no flavour and title with flavours produces action to add empty flavour
    """
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
    book = create_book(
        flavour="",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    title = create_title(
        name="test_en_all",
        flavours=["maxi", "mini"],
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    flavour_actions = [
        action for action in actions if action.kind == "create_title_flavour"
    ]
    assert len(flavour_actions) == 1
    assert flavour_actions[0].requirement == "mandatory"
    assert flavour_actions[0].data["flavour"] == ""


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_recipe_issue(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """
    Book with different recipe from title flavour produces action to update title
    flavour
    """
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
    book = create_book(
        flavour="maxi",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    book.recipe_id = uuid4()
    dbsession.add(book)

    title = create_title(
        name="test_en_all",
        flavours=["maxi", "mini"],
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
        recipe_id=uuid4(),
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    recipe_actions = [
        action for action in actions if action.kind == "update_flavour_recipe"
    ]
    assert len(recipe_actions) == 1
    assert recipe_actions[0].requirement == "mandatory"
    assert recipe_actions[0].data["recipe_id"] == book.recipe_id


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_flavour_mismatch_add_flavour(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Book with a flavour not in title produces create_title_flavour action
    with book flavour in title flavours
    """
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
    book = create_book(
        flavour="nopic",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    title = create_title(
        name="test_en_all",
        flavours=["maxi", "mini"],
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    flavour_actions = [
        action for action in actions if action.kind == "create_title_flavour"
    ]
    assert len(flavour_actions) == 1
    assert flavour_actions[0].requirement == "mandatory"
    assert flavour_actions[0].data["flavour"] == "nopic"


def test_promotion_actions_multiple_actions(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Book requiring multiple fixes produces all relevant actions."""
    # Ensure scraper is NOT whitelisted
    monkeypatch.setattr(
        "cms_backend.context.Context.zimcheck_scrapers_whitelist_regex", None
    )
    book = create_book(
        flavour="nopic",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Updated Title",
            "Creator": "Updated Creator",
            "Publisher": "Updated Publisher",
            "Date": "2025-01-01",
            "Description": "Updated description",
            "Language": "xxx",  # unsupported
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    book.zimcheck_summary = {
        "zimcheck_version": "1.0.0",
        "status": False,
        "checks": ["internal_urls"],
        "error_count": 2,
        "warning_count": 0,
        "retcode": 1,
    }
    # Title: no collections, different metadata (missing Title), not stable maturity
    title = create_title(
        name="test_en_all",
        flavours=["maxi"],
        title=None,
        creator="Old Creator",
        publisher="Old Publisher",
        description="Old description",
        language="xxx",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)

    kinds = {action.kind for action in actions}
    assert "unknown_languages" in kinds
    assert "zimcheck_issues" in kinds
    assert "update_title_metadata" in kinds
    assert "update_title_maturity" in kinds
    assert "set_title_collections" in kinds
    assert "create_title_flavour" in kinds


@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_media_count_issue(
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection_title: Callable[..., CollectionTitle],
    illustration_48x48_at_1: str,
):
    """A book with all media count issue returns media count action"""
    mock_get_zimcheck_errors.return_value = []
    book = create_book(
        flavour="maxi",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
        article_count=105,
        media_count=115,
    )
    title = create_title(
        name="test_en_all",
        flavours=["maxi"],
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    title.maturity = "stable"  # override default "unstable"
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    create_collection_title(
        title=title,
        media_count_increase_threshold=0.1,
        article_count_increase_threshold=0.1,
        media_count_decrease_threshold=0.1,
        article_count_decrease_threshold=0.1,
    )

    # create the latest book with media_count of 100 and article count of 105
    create_book(
        article_count=105,
        media_count=100,
        flavour="maxi",
        title_id=title.id,
        location_kind="prod",
    )

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 1
    assert actions[0].requirement == "information"
    assert actions[0].kind == "media_count"


@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_article_count_issue(
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection_title: Callable[..., CollectionTitle],
    illustration_48x48_at_1: str,
):
    """A book with article count issue returns article count action"""
    mock_get_zimcheck_errors.return_value = []
    book = create_book(
        flavour="maxi",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
        article_count=115,
        media_count=100,
    )
    title = create_title(
        name="test_en_all",
        flavours=["maxi"],
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    title.maturity = "stable"  # override default "unstable"
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    create_collection_title(
        title=title,
        media_count_increase_threshold=0.1,
        article_count_increase_threshold=0.1,
        media_count_decrease_threshold=0.1,
        article_count_decrease_threshold=0.1,
    )

    # create the latest book with media_count of 100 and article count of 100
    create_book(
        article_count=100,
        media_count=100,
        flavour="maxi",
        title_id=title.id,
        location_kind="prod",
    )

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 1
    assert actions[0].requirement == "information"
    assert actions[0].kind == "article_count"


@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promotion_actions_ready_for_prod(
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection_title: Callable[..., CollectionTitle],
    illustration_48x48_at_1: str,
):
    """A book with all prerequisites met returns no actions."""
    mock_get_zimcheck_errors.return_value = []
    book = create_book(
        flavour="maxi",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    title = create_title(
        name="test_en_all",
        flavours=["maxi"],
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    title.maturity = "stable"  # override default "unstable"
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    create_collection_title(title=title)

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 0


@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_promote_book_with_no_actions_move_directly_to_prod(
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection_title: Callable[..., CollectionTitle],
    create_book_location: Callable[..., BookLocation],
    create_warehouse: Callable[..., Warehouse],
    illustration_48x48_at_1: str,
    account: Account,
):
    """Test applying empty actions on a book with no issues simply moves book to prod"""
    mock_get_zimcheck_errors.return_value = []
    warehouse = create_warehouse()

    book = create_book(
        flavour="maxi",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator",
            "Publisher": "Test Publisher",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    title = create_title(
        name="test_en_all",
        flavours=["maxi"],
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    title.maturity = "stable"
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    create_collection_title(title=title)

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 0
    assert book.location_kind == "quarantine"

    apply_book_promotion_actions(
        dbsession, book_id=book.id, actions=[], author_id=account.id
    )
    assert book.location_kind == "prod"


def test_apply_actions_duplicate_actions_raises_error(
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Providing duplicate action kinds raises ValueError."""
    book = _create_valid_book(create_book, illustration_48x48_at_1)
    title = _create_valid_title(create_title, illustration_48x48_at_1)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"duplicates"):
        apply_book_promotion_actions(
            dbsession,
            book_id=book.id,
            actions=[
                BaseBookPromotionAction(
                    kind="update_title_maturity",
                    data={"maturity": "stable"},
                    requirement="optional",
                ),
                BaseBookPromotionAction(
                    kind="update_title_maturity",
                    data={"maturity": "stable"},
                    requirement="optional",
                ),
            ],
            author_id=uuid4(),
        )


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_unknown_action_raises_error(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_collection_title: Callable[..., CollectionTitle],
    illustration_48x48_at_1: str,
):
    """Providing an action not in expected actions raises ValueError."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    book = _create_valid_book(create_book, illustration_48x48_at_1)
    title = _create_valid_title(create_title, illustration_48x48_at_1)
    title.maturity = "stable"
    book.title = title
    dbsession.add(book)
    dbsession.flush()
    create_collection_title(title=title)

    with pytest.raises(ValueError, match=r"Unexpected actions"):
        apply_book_promotion_actions(
            dbsession,
            book_id=book.id,
            actions=[
                BaseBookPromotionAction(
                    kind="create_title",
                    data={},
                    requirement="mandatory",
                ),
            ],
            author_id=uuid4(),
        )


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_required_mismatch_raises_error(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Marking an optional action as required raises ValueError."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    book = _create_valid_book(create_book, illustration_48x48_at_1)
    title = _create_valid_title(create_title, illustration_48x48_at_1)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"mandatory actions"):
        apply_book_promotion_actions(
            dbsession,
            book_id=book.id,
            actions=[
                BaseBookPromotionAction(
                    kind="update_title_maturity",
                    data={"maturity": "stable"},
                    requirement="mandatory",  # should be "optional"
                ),
            ],
            author_id=uuid4(),
        )


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_restore_title_wrong_name_raises_error(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_collection_title: Callable[..., CollectionTitle],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
):
    """Restoring with a title name different from the book's title raises ValueError."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    book = _create_valid_book(create_book, illustration_48x48_at_1)
    title = create_title(
        name="test_en_all",
        archived=True,
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    create_collection_title(title=title)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"Only the book's title should be specified"):
        apply_book_promotion_actions(
            dbsession,
            book_id=book.id,
            actions=[
                BaseBookPromotionAction(
                    kind="restore_title",
                    data={"title_names": ["wrong_title"]},
                    requirement="mandatory",
                ),
            ],
            author_id=uuid4(),
        )


@pytest.mark.parametrize(
    "collection_titles",
    [
        pytest.param({}, id="no-collection-tilles"),
        pytest.param({"collection_titles": []}, id="empty-collection-titles"),
    ],
)
@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_update_collections_without_entries_raises_error(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
    collection_titles: dict[str, Any],
):
    """Applying set_title_collections with empty entries raises ValueError."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    book = _create_valid_book(create_book, illustration_48x48_at_1)
    title = _create_valid_title(create_title, illustration_48x48_at_1)
    title.maturity = "stable"
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    with pytest.raises(ValueError, match=r"must provide collection details"):
        apply_book_promotion_actions(
            dbsession,
            book_id=book.id,
            actions=[
                BaseBookPromotionAction(
                    kind="set_title_collections",
                    data=collection_titles,
                    requirement="mandatory",
                ),
            ],
            author_id=uuid4(),
        )


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_action_update_recipe_flavour(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_book_location: Callable[..., BookLocation],
    create_title: Callable[..., Title],
    create_collection_title: Callable[..., CollectionTitle],
    create_warehouse: Callable[..., Warehouse],
    illustration_48x48_at_1: str,
    account: Account,
):
    """
    Test apply action to fix a recipe issue
    """
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    warehouse = create_warehouse()
    book = _create_valid_book(create_book, illustration_48x48_at_1)
    book.flavour = "maxi"
    book.recipe_id = uuid4()
    dbsession.add(book)

    title = create_title(
        name="test_en_all",
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
        flavours=["maxi", "mini"],
        recipe_id=uuid4(),
    )
    title.maturity = "stable"
    dbsession.add(title)

    create_collection_title(title=title)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 1
    assert actions[0].kind == "update_flavour_recipe"

    action = actions[0]
    apply_book_promotion_actions(
        dbsession,
        book_id=book.id,
        author_id=account.id,
        actions=[
            BaseBookPromotionAction(
                kind=action.kind, data=action.data, requirement=action.requirement
            )
        ],
    )
    dbsession.refresh(book)
    assert book_has_recipe_issue(book) is False


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_create_title(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_collection: Callable[..., Collection],
    create_warehouse: Callable[..., Warehouse],
    create_book_location: Callable[..., BookLocation],
    illustration_48x48_at_1: str,
    account: Account,
):
    """Applying a create_title action creates a new title."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    warehouse = create_warehouse()
    book = create_book(
        name="test_en_all",
        flavour="maxi",
        zim_metadata=_make_metadata(illustration_48x48_at_1),
        location_kind="quarantine",
    )
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    collection = create_collection(name="mycollection")

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 1
    assert actions[0].kind == "create_title"

    # Fill in the collection details
    apply_data = dict(actions[0].data)
    apply_data["collection_titles"] = [
        {"collection_name": collection.name, "path": "/test/path"}
    ]

    apply_book_promotion_actions(
        dbsession,
        book_id=book.id,
        actions=[
            BaseBookPromotionAction(
                kind="create_title",
                data=apply_data,
                requirement="mandatory",
            ),
        ],
        author_id=account.id,
    )

    # Verify the title was created
    title = dbsession.query(Title).filter(Title.name == "test_en_all").one_or_none()
    assert title is not None
    assert title.title == "Test Article"
    assert title.maturity == "stable"
    assert len(title.collections) == 1
    dbsession.refresh(book)
    assert book.title_id == title.id
    assert book.location_kind == "prod"
    assert book.needs_file_operation
    assert len(title.flavours) == 1
    assert title.flavours[0].last_book_added_at is not None


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_create_title_fixed_collection_titles(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_warehouse: Callable[..., Warehouse],
    create_book_location: Callable[..., BookLocation],
    illustration_48x48_at_1: str,
    account: Account,
    requested_task: RequestedTask,
):
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    warehouse = create_warehouse()
    book = create_book(
        name="test_en_all",
        flavour="maxi",
        zim_metadata=_make_metadata(illustration_48x48_at_1),
        location_kind="quarantine",
    )
    book.recipe_id = requested_task.recipe_id

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 1
    assert actions[0].kind == "create_title"

    apply_book_promotion_actions(
        dbsession,
        book_id=book.id,
        actions=[
            BaseBookPromotionAction(
                kind="create_title",
                data=actions[0].data,
                requirement="mandatory",
            ),
        ],
        author_id=account.id,
    )

    # Verify the title was created
    title = dbsession.query(Title).filter(Title.name == "test_en_all").one_or_none()
    assert title is not None
    assert title.title == "Test Article"
    assert title.maturity == "stable"
    assert len(title.collections) == 1
    assert str(title.collections[0].path) == requested_task.collection_path
    dbsession.refresh(book)
    assert book.title_id == title.id
    assert book.location_kind == "prod"
    assert book.needs_file_operation
    assert len(title.flavours) == 1
    assert title.flavours[0].last_book_added_at is not None


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_create_title_modify_fixed_collection_titles(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_warehouse: Callable[..., Warehouse],
    create_book_location: Callable[..., BookLocation],
    create_collection: Callable[..., Collection],
    illustration_48x48_at_1: str,
    account: Account,
    requested_task: RequestedTask,
):
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    warehouse = create_warehouse()
    book = create_book(
        name="test_en_all",
        flavour="maxi",
        zim_metadata=_make_metadata(illustration_48x48_at_1),
        location_kind="quarantine",
    )
    book.recipe_id = requested_task.recipe_id

    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )

    collection = create_collection(name="mycollection")
    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    assert len(actions) == 1
    assert actions[0].kind == "create_title"

    # Fill in the collection details with different collection information
    apply_data = dict(actions[0].data)
    apply_data["collection_titles"] = [
        {"collection_name": collection.name, "path": "/test/path"}
    ]

    with pytest.raises(
        ValueError, match="Expected collection titles for action differ"
    ):
        apply_book_promotion_actions(
            dbsession,
            book_id=book.id,
            actions=[
                BaseBookPromotionAction(
                    kind="create_title",
                    data=apply_data,
                    requirement="mandatory",
                ),
            ],
            author_id=account.id,
        )


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_restore_title(
    mock_get_zimcheck_errors: MagicMock,
    mock_get_book_unsupported_languages: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_title: Callable[..., Title],
    create_warehouse: Callable[..., Warehouse],
    create_book_location: Callable[..., BookLocation],
    create_collection_title: Callable[..., CollectionTitle],
    illustration_48x48_at_1: str,
    account: Account,
):
    """Applying a restore_title action restores an archived title."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []

    warehouse = create_warehouse()
    book = _create_valid_book(create_book, illustration_48x48_at_1)
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    title = create_title(
        name="test_en_all",
        archived=True,
        title="Test Article",
        creator="Test Creator",
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    create_collection_title(title=title)
    book.title = title
    dbsession.add(book)
    dbsession.flush()

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    restore_actions = [a for a in actions if a.kind == "restore_title"]
    assert len(restore_actions) == 1

    apply_book_promotion_actions(
        dbsession,
        book_id=book.id,
        actions=[
            BaseBookPromotionAction(
                kind="restore_title",
                data={"title_names": ["test_en_all"]},
                requirement="mandatory",
            ),
        ],
        author_id=account.id,
    )

    dbsession.refresh(title)
    assert title.archived is False
    dbsession.refresh(book)
    assert book.location_kind == "prod"
    assert book.needs_file_operation


@patch("cms_backend.db.book_actions.get_book_unsupported_languages")
@patch("cms_backend.db.book_actions.get_zimcheck_errors")
def test_apply_actions_batched_updates(
    mock_get_book_unsupported_languages: MagicMock,
    mock_get_zimcheck_errors: MagicMock,
    dbsession: OrmSession,
    create_book: Callable[..., Book],
    create_warehouse: Callable[..., Warehouse],
    create_book_location: Callable[..., BookLocation],
    create_title: Callable[..., Title],
    create_collection: Callable[..., Collection],
    illustration_48x48_at_1: str,
    account: Account,
):
    """Multiple update_title_* actions are batched into a single update call."""
    mock_get_zimcheck_errors.return_value = []
    mock_get_book_unsupported_languages.return_value = []
    warehouse = create_warehouse()
    book = create_book(
        flavour="nopic",
        zim_metadata={
            "Name": "test_en_all",
            "Title": "Test Article",
            "Creator": "Test Creator 2",
            "Publisher": "openZIM",
            "Date": "2025-01-01",
            "Description": "Test description",
            "Language": "eng",
            "Illustration_48x48@1": illustration_48x48_at_1,
        },
        location_kind="quarantine",
    )
    create_book_location(
        book=book,
        warehouse_id=warehouse.id,
        path=Path("zim"),
        filename="test_en_all_2024-01.zim",
        status="current",
    )
    title = create_title(
        name="test_en_all",
        title="Test Article",
        creator=None,  # missing
        publisher="Test Publisher",
        description="Test description",
        language="eng",
        illustration_48x48_at_1=illustration_48x48_at_1,
    )
    book.title = title
    dbsession.add(book)
    dbsession.flush()
    collection = create_collection(name="mycollection")

    actions = get_book_promotion_actions(dbsession, book_id=book.id)
    kinds = {a.kind for a in actions}
    assert "update_title_metadata" in kinds  # creator differs/missing
    assert "update_title_maturity" in kinds  # default "unstable"
    assert "set_title_collections" in kinds  # no collections
    assert "create_title_flavour" in kinds  # flavour mismatch

    # Build apply actions from the generated ones
    apply_actions: list[BaseBookPromotionAction] = []
    for action in actions:
        data = dict(action.data)
        if action.kind == "set_title_collections":
            data["collection_titles"] = [
                {"collection_name": collection.name, "path": "/test/path"}
            ]
        apply_actions.append(
            BaseBookPromotionAction(
                kind=action.kind,
                data=data,
                requirement=action.requirement,
            )
        )

    apply_book_promotion_actions(
        dbsession,
        book_id=book.id,
        actions=apply_actions,
        author_id=account.id,
    )

    dbsession.refresh(title)
    assert title.creator == "Test Creator 2"
    assert title.maturity == "stable"
    assert len(title.collections) == 1
    dbsession.refresh(book)
    assert book.location_kind == "prod"
    assert book.needs_file_operation


def _make_metadata(illustration_48x48_at_1: str) -> dict[str, Any]:
    """Return valid ZIM metadata for a test book."""
    return {
        "Name": "test_en_all",
        "Title": "Test Article",
        "Creator": "Test Creator",
        "Publisher": "Test Publisher",
        "Date": "2025-01-01",
        "Description": "Test description",
        "Language": "eng",
        "Illustration_48x48@1": illustration_48x48_at_1,
    }


def _create_valid_book(
    create_book: Callable[..., Book],
    illustration_48x48_at_1: str,
) -> Book:
    """Create a book with all mandatory metadata, in quarantine, ready for promotion."""
    return create_book(
        zim_metadata=_make_metadata(illustration_48x48_at_1),
        location_kind="quarantine",
    )


def _create_valid_title(
    create_title: Callable[..., Title],
    illustration_48x48_at_1: str,
    **kwargs: Any,
) -> Title:
    """Create a title with full mandatory metadata."""
    defaults: dict[str, Any] = {
        "name": "test_en_all",
        "title": "Test Article",
        "creator": "Test Creator",
        "publisher": "Test Publisher",
        "description": "Test description",
        "language": "eng",
        "illustration_48x48_at_1": illustration_48x48_at_1,
    }
    defaults.update(kwargs)
    return create_title(**defaults)
