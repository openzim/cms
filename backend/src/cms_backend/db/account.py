from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import (
    RecordAlreadyExistsError,
    RecordDoesNotExistError,
)
from cms_backend.db.models import Account
from cms_backend.roles import ROLES, RoleEnum, merge_scopes
from cms_backend.schemas.models import AccountUpdateSchema
from cms_backend.schemas.orms import AccountSchema, ListResult
from cms_backend.utils import is_valid_uuid


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


def get_account_by_identifier_or_none(
    session: OrmSession, *, account_identifier: str
) -> Account | None:
    """Get an account or None by either username (str) or account_id (UUID)"""
    if is_valid_uuid(account_identifier):
        return get_account_by_id_or_none(session, account_id=UUID(account_identifier))

    return get_account_by_username_or_none(session, username=account_identifier)


def get_account_by_identifier(session: OrmSession, *, account_identifier: str):
    """Get an account by either username(str) or account_id(UUID).

    Raises RecordDoestNotExistError if account not found.
    """
    if (
        account := get_account_by_identifier_or_none(
            session,
            account_identifier=account_identifier,
        )
    ) is None:
        raise RecordDoesNotExistError(
            f"Account with identifier {account_identifier} does not exist"
        )
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
        id=account.id,
        idp_sub=account.idp_sub,
        display_name=account.display_name,
        role=account.role,
        scope=merge_scopes(ROLES.get(account.role, {}), ROLES[RoleEnum.EDITOR]),
        has_password=account.password_hash is not None,
    )


def create_account(
    session: OrmSession,
    *,
    display_name: str,
    username: str | None = None,
    password_hash: str | None = None,
    role: str = "custom",
    idp_sub: UUID | None = None,
) -> Account:
    """Create a new account"""
    account = Account(
        username=username,
        display_name=display_name,
        password_hash=password_hash,
        role=role,
        deleted=False,
        idp_sub=idp_sub,
    )
    session.add(account)
    try:
        session.flush()
    except IntegrityError as exc:
        raise RecordAlreadyExistsError("Account already exists") from exc
    return account


def delete_account(
    session: OrmSession,
    *,
    account_id: UUID,
) -> None:
    """Delete an account"""
    session.execute(
        update(Account).where(Account.id == account_id).values(deleted=True)
    )


def get_accounts(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    username: str | None = None,
    show_zimfarmers: bool = True,
    show_viewers: bool = True,
) -> ListResult[Account]:
    """Get a list of accounts"""
    query = (
        select(
            func.count().over().label("nb_records"),
            Account,
        )
        .where(
            Account.deleted.is_(False),
            (Account.role != RoleEnum.ZIMFARM) | (show_zimfarmers is True),
            (Account.role != RoleEnum.VIEWER) | (show_viewers is True),
            (
                Account.display_name.ilike(
                    f"%{username if username is not None else ''}%"
                )
            )
            | (username is None),
        )
        .offset(skip)
        .limit(limit)
        .order_by(Account.display_name.asc(), Account.id.asc())
    )

    results = ListResult[Account](nb_records=0, records=[])
    for nb_records, account in session.execute(query).all():
        results.nb_records = nb_records
        results.records.append(account)
    return results


def update_account_password(
    session: OrmSession,
    *,
    account_id: UUID,
    password_hash: str | None,
) -> None:
    """Update an account's password"""
    session.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(password_hash=password_hash)
    )


def update_account(
    session: OrmSession, *, account_id: str | UUID, request: AccountUpdateSchema
) -> None:
    """Update an account"""
    account = get_account_by_identifier(session, account_identifier=str(account_id))

    values = request.model_dump(exclude_unset=True, mode="json")

    if "display_name" in values and not values["display_name"]:
        raise ValueError("Account must have a display name.")

    # Allow blank username only if an account does not have password set.
    if account.password_hash is not None and (
        "username" in values and not values["username"]
    ):
        raise ValueError("Account with password must have a username.")

    if (role := values.get("role")) is not None:
        values["role"] = role

    if not values:
        return

    session.execute(update(Account).where(Account.id == account.id).values(**values))
