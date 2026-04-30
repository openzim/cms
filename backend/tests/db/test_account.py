from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.account import (
    delete_account,
    get_account_by_id,
    get_account_by_id_or_none,
    get_account_by_username,
    get_account_by_username_or_none,
    get_accounts,
    update_account,
)
from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import Account
from cms_backend.roles import RoleEnum, merge_scopes
from cms_backend.schemas.models import AccountUpdateSchema


@pytest.mark.parametrize(
    ["custom_scope", "all_scopes", "expected"],
    [
        (
            {"book": {"read": True}},
            {
                "book": {"read": True, "write": True},
                "title": {"read": True, "write": True},
            },
            {
                "book": {"read": True, "write": False},
                "title": {"read": False, "write": False},
            },
        ),
        (
            {},
            {
                "book": {"read": True, "write": True},
                "title": {"read": True, "write": True},
            },
            {
                "book": {"read": False, "write": False},
                "title": {"read": False, "write": False},
            },
        ),
    ],
)
def test_merge_scopes(
    custom_scope: dict[str, dict[str, bool]],
    all_scopes: dict[str, dict[str, bool]],
    expected: dict[str, dict[str, bool]],
):
    assert merge_scopes(custom_scope, all_scopes) == expected


def test_get_account_by_id_or_none(dbsession: OrmSession):
    """Test that get_account_by_id_or_none returns None if the account does not exist"""
    account = get_account_by_id_or_none(dbsession, account_id=uuid4())
    assert account is None


def test_get_account_by_id_not_found(dbsession: OrmSession):
    """Test that get_account_by_id raises an exception if the account does not exist"""
    with pytest.raises(RecordDoesNotExistError):
        get_account_by_id(dbsession, account_id=uuid4())


def test_get_account_by_id(dbsession: OrmSession, account: Account):
    """Test that get_account_by_id returns the account if the account exists"""
    db_account = get_account_by_id(dbsession, account_id=account.id)
    assert db_account is not None
    assert db_account.id == account.id


def test_get_account_by_username_or_none(dbsession: OrmSession):
    """
    Test that get_account_by_username_or_none returns None if the account does not exist
    """
    account = get_account_by_username_or_none(dbsession, username="doesnotexist")
    assert account is None


def test_get_account_by_username_not_found(dbsession: OrmSession):
    """
    Test that get_account_by_username raises an exception if the account does not exist
    """
    with pytest.raises(RecordDoesNotExistError):
        get_account_by_username(dbsession, username="doesnotexist")


def test_delete_account(dbsession: OrmSession, account: Account):
    """Test that delete_account marks account as deleted"""
    delete_account(dbsession, account_id=account.id)
    dbsession.refresh(account)
    assert account.deleted


@pytest.mark.parametrize("show_zimfarmers", [True, False])
def test_get_accounts_filter_workers(
    dbsession: OrmSession,
    create_account: Callable[..., Account],
    *,
    show_zimfarmers: bool,
):
    """Test that get_accounts filters zimfarm accounts."""
    create_account(permission=RoleEnum.ZIMFARM)

    results = get_accounts(dbsession, skip=0, limit=1, show_zimfarmers=show_zimfarmers)
    if show_zimfarmers:
        assert results.nb_records == 1
        assert len(results.records) == 1
    else:
        assert results.nb_records == 0
        assert len(results.records) == 0


def test_update_account_partial(dbsession: OrmSession, account: Account):
    """Test that update_account can update partial fields"""
    update_account(
        dbsession,
        account_id=account.id,
        request=AccountUpdateSchema(role=RoleEnum.EDITOR, display_name="newdisplay"),
    )
    dbsession.refresh(account)
    assert account.role == RoleEnum.EDITOR
    assert account.display_name == "newdisplay"


def test_update_account_no_display_name(dbsession: OrmSession, account: Account):
    with pytest.raises(ValueError, match="Account must have a display name."):
        update_account(
            dbsession,
            account_id=account.id,
            request=AccountUpdateSchema(display_name=None),
        )


def test_update_account_with_password_set_blank_username(
    dbsession: OrmSession, create_account: Callable[..., Account]
):
    account = create_account(password="testpassword")
    with pytest.raises(ValueError, match="Account with password must have a username"):
        update_account(
            dbsession, account_id=account.id, request=AccountUpdateSchema(username=None)
        )
