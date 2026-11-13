from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import flavour as db_flavour
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account, Book, Title, TitleFlavour
from cms_backend.db.title import delete_title_flavour


@pytest.mark.parametrize(
    "skip,limit,expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 1, id="second-page"),
        pytest.param(8, 3, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 20, 4, id="first-page-with-high-limit"),
    ],
)
def test_get_title_flavours_pagination(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test that get_title_flavours works correctly with skip and limit"""

    title = create_title(name="wikipedia_en_all")
    flavours = ["maxi", "mini", "nopic", ""]
    for flavour in flavours:
        tf = TitleFlavour(flavour=flavour, recipe_id=None)
        tf.title = title
        dbsession.add(tf)
        dbsession.flush()

    results = db_flavour.get_title_flavours(
        dbsession, title_id=title.id, limit=limit, skip=skip
    )

    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_update_title_flavour_archived_and_restore(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
):
    """Archiving a flavour only flags it, keeping the flavour and its books."""
    title = create_title(name="wikipedia_en_all", flavours=["maxi", "mini"])
    initial_history_count = len(title.history_entries)

    archived = db_flavour.update_title_flavour(
        dbsession, title, "maxi", author_id=account.id, archived=True
    )
    assert archived.archived is True
    assert db_flavour.get_title_flavour(dbsession, title.id, "maxi").archived is True
    assert any("hidden from catalog" in event for event in title.events)
    assert len(title.history_entries) == initial_history_count + 1

    restored = db_flavour.update_title_flavour(
        dbsession, title, "maxi", author_id=account.id, archived=False
    )
    assert restored.archived is False
    assert db_flavour.get_title_flavour(dbsession, title.id, "maxi").archived is False
    assert any("restored to catalog" in event for event in title.events)

    assert {tf.flavour for tf in title.flavours} == {"maxi", "mini"}


def test_update_title_flavour_temporary_manual_review(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
):
    """Temporary manual review can be enabled and disabled for a flavour."""
    title = create_title(name="wikipedia_en_all", flavours=["maxi", "mini"])

    enabled = db_flavour.update_title_flavour(
        dbsession,
        title,
        "maxi",
        author_id=account.id,
        temporary_manual_review=True,
    )
    assert enabled.temporary_manual_review is True
    assert any("temporary manual review enabled" in event for event in title.events)

    disabled = db_flavour.update_title_flavour(
        dbsession,
        title,
        "maxi",
        author_id=account.id,
        temporary_manual_review=False,
    )
    assert disabled.temporary_manual_review is False
    assert any("temporary manual review disabled" in event for event in title.events)


def test_update_title_flavour_unknown_flavour(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
):
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    with pytest.raises(RecordDoesNotExistError):
        db_flavour.update_title_flavour(
            dbsession, title, "mini", author_id=account.id, archived=True
        )


def test_update_title_flavour_requires_a_field(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
):
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    with pytest.raises(ValueError, match=r"At least one"):
        db_flavour.update_title_flavour(dbsession, title, "maxi", author_id=account.id)


def test_update_title_flavour_already_in_state(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
):
    title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    with pytest.raises(RecordDoesNotExistError):
        db_flavour.update_title_flavour(
            dbsession, title, "maxi", author_id=account.id, archived=False
        )

    db_flavour.update_title_flavour(
        dbsession, title, "maxi", author_id=account.id, archived=True
    )
    with pytest.raises(RecordDoesNotExistError):
        db_flavour.update_title_flavour(
            dbsession, title, "maxi", author_id=account.id, archived=True
        )


@patch("cms_backend.db.book.delete_book")
def test_delete_title_flavour(
    mock_delete_book: MagicMock,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    title = create_title(name="wikipedia_en_all")
    tf = TitleFlavour(flavour="maxi", recipe_id=None)
    tf.title = title
    dbsession.add(tf)
    dbsession.flush()
    create_book(flavour="maxi", title_id=title.id)
    delete_title_flavour(dbsession, title, tf.flavour)
    mock_delete_book.assert_called_once()
    assert (
        dbsession.scalars(
            select(TitleFlavour).where(
                TitleFlavour.flavour == tf.flavour, TitleFlavour.title_id == title.id
            )
        ).one_or_none()
        is None
    )
