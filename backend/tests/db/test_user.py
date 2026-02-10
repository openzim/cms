from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import (
    RecordDoesNotExistError,
)
from cms_backend.db.models import User
from cms_backend.db.user import (
    delete_user,
    get_user_by_id,
    get_user_by_id_or_none,
    get_user_by_username,
    get_user_by_username_or_none,
)
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


def test_get_user_by_id_or_none(dbsession: OrmSession):
    """Test that get_user_by_id_or_none returns None if the user does not exist"""
    user = get_user_by_id_or_none(dbsession, user_id=uuid4())
    assert user is None


def test_get_user_by_id_not_found(dbsession: OrmSession):
    """Test that get_user_by_id raises an exception if the user does not exist"""
    with pytest.raises(RecordDoesNotExistError):
        get_user_by_id(dbsession, user_id=uuid4())


def test_get_user_by_id(dbsession: OrmSession, user: User):
    """Test that get_user_by_id returns the user if the user exists"""
    db_user = get_user_by_id(dbsession, user_id=user.id)
    assert db_user is not None
    assert db_user.id == user.id


def test_get_user_by_username_or_none(dbsession: OrmSession):
    """Test that get_user_by_username_or_none returns None if the user does not exist"""
    user = get_user_by_username_or_none(dbsession, username="doesnotexist")
    assert user is None


def test_get_user_by_username_not_found(dbsession: OrmSession):
    """Test that get_user_by_username raises an exception if the user does not exist"""
    with pytest.raises(RecordDoesNotExistError):
        get_user_by_username(dbsession, username="doesnotexist")


def test_delete_user(dbsession: OrmSession, user: User):
    """Test that delete_user marks user as deleted"""
    delete_user(dbsession, user_id=user.id)
    dbsession.refresh(user)
    assert user.deleted
