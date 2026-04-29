from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import (
    RecordAlreadyExistsError,
    RecordDoesNotExistError,
)
from cms_backend.db.models import Account
from cms_backend.roles import ROLES, RoleEnum, merge_scopes
from cms_backend.schemas.orms import AccountSchema


def get_account_by_username_or_none(
    session: OrmSession, *, username: str
) -> Account | None:
    """Get an account by username or return None if the account does not exist"""
    return session.scalars(
        select(Account).where(Account.username == username)
    ).one_or_none()


def get_account_by_username(session: OrmSession, *, username: str) -> Account:
    """Get an account by username or raise an exception if the account does not exist"""
    if (account := get_account_by_username_or_none(session, username=username)) is None:
        raise RecordDoesNotExistError(
            f"Account with username {username} does not exist"
        )
    return account


def get_account_by_id_or_none(
    session: OrmSession, *, account_id: UUID
) -> Account | None:
    """Get an account by id or return None if the account does not exist"""
    return session.scalars(
        select(Account).where(
            (Account.idp_sub == account_id) | (Account.id == account_id)
        )
    ).one_or_none()


def get_account_by_id(session: OrmSession, *, account_id: UUID) -> Account:
    """Get an account by id or raise an exception if the account does not exist"""
    if (account := get_account_by_id_or_none(session, account_id=account_id)) is None:
        raise RecordDoesNotExistError(f"Account with id {account_id} does not exist")
    return account


def check_account_permission(
    account: Account,
    *,
    namespace: str,
    name: str,
) -> bool:
    """Check if an account has a permission for a given namespace and name"""
    # Select the scope that comes with their role enum or scope from the DB
    scope = ROLES.get(account.role)
    if not scope:
        return False
    return scope.get(namespace, {}).get(name, False)


def create_account_schema(account: Account) -> AccountSchema:
    return AccountSchema(
        username=account.username,
        role=account.role,
        scope=merge_scopes(ROLES.get(account.role, {}), ROLES[RoleEnum.EDITOR]),
    )


def create_account(
    session: OrmSession,
    *,
    username: str,
    role: str,
    idp_sub: UUID | None = None,
    password_hash: str | None = None,
) -> Account:
    """Create a new account"""
    account = Account(
        username=username,
        role=role,
        deleted=False,
        idp_sub=idp_sub,
        password_hash=password_hash,
    )
    session.add(account)
    try:
        session.flush()
    except IntegrityError as exc:
        raise RecordAlreadyExistsError("Account already exists") from exc
    return account


def update_account_password(
    session: OrmSession,
    *,
    account_id: UUID,
    password_hash: str,
) -> None:
    """Update an account's password"""
    session.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(password_hash=password_hash)
    )


def delete_account(
    session: OrmSession,
    *,
    account_id: UUID,
) -> None:
    """Delete an account"""
    session.execute(
        update(Account).where(Account.id == account_id).values(deleted=True)
    )
