from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import (
    RecordAlreadyExistsError,
    RecordDoesNotExistError,
)
from cms_backend.db.models import User
from cms_backend.roles import ROLES, RoleEnum, merge_scopes
from cms_backend.schemas.orms import UserSchema


def get_user_by_username_or_none(session: OrmSession, *, username: str) -> User | None:
    """Get a user by username or return None if the user does not exist"""
    return session.scalars(select(User).where(User.username == username)).one_or_none()


def get_user_by_username(session: OrmSession, *, username: str) -> User:
    """Get a user by username or raise an exception if the user does not exist"""
    if (user := get_user_by_username_or_none(session, username=username)) is None:
        raise RecordDoesNotExistError(f"User with username {username} does not exist")
    return user


def get_user_by_id_or_none(session: OrmSession, *, user_id: UUID) -> User | None:
    """Get a user by id or return None if the user does not exist"""
    return session.scalars(select(User).where(User.idp_sub == user_id)).one_or_none()


def get_user_by_id(session: OrmSession, *, user_id: UUID) -> User:
    """Get a user by id or raise an exception if the user does not exist"""
    if (user := get_user_by_id_or_none(session, user_id=user_id)) is None:
        raise RecordDoesNotExistError(f"User with id {user_id} does not exist")
    return user


def check_user_permission(
    user: User,
    *,
    namespace: str,
    name: str,
) -> bool:
    """Check if a user has a permission for a given namespace and name"""
    # Select the scope that comes with their role enum or scope from the DB
    scope = ROLES.get(user.role)
    if not scope:
        return False
    return scope.get(namespace, {}).get(name, False)


def create_user_schema(user: User) -> UserSchema:
    return UserSchema(
        username=user.username,
        role=user.role,
        idp_sub=user.idp_sub,
        scope=merge_scopes(ROLES.get(user.role, {}), ROLES[RoleEnum.EDITOR]),
    )


def create_user(
    session: OrmSession,
    *,
    username: str,
    role: str,
    idp_sub: UUID,
) -> User:
    """Create a new user"""
    user = User(
        username=username,
        role=role,
        deleted=False,
        idp_sub=idp_sub,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        raise RecordAlreadyExistsError("User already exists") from exc
    return user
