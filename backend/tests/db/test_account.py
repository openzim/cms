from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.account import (
    delete_account,
    get_account_by_id,
    get_account_by_id_or_none,
    get_account_by_username,
    get_account_by_username_or_none,
)
from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import Account
from cms_backend.roles import merge_scopes


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
