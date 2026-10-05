from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Account, TitlePermission
from cms_backend.roles import RoleEnum


def get_accessible_title_ids(
    session: OrmSession, account: Account | None
) -> Sequence[UUID] | None:
    """Get the title IDs an account is explicitly allowed to operate on.

    NOTE: None implies there is no title-level restriction, in which case access
    is governed solely by collection access. An empty sequence means the account
    has no title-level grant at all.
    """
    if account is None or RoleEnum(account.role) != RoleEnum.TITLE_UPLOADER:
        return None

    return session.scalars(
        select(TitlePermission.title_id).where(TitlePermission.account_id == account.id)
    ).all()


def create_title_permission(session: OrmSession, title_id: UUID, account_id: UUID):
    """Create a title permission for the current account on the title"""
    permission = TitlePermission(title_id=title_id, account_id=account_id)
    session.add(permission)
    session.flush()


def delete_title_permissions(session: OrmSession, account_id: UUID):
    """Delete all title permissions for account"""
    session.execute(
        delete(TitlePermission).where(TitlePermission.account_id == account_id)
    )


def get_title_uploaders(session: OrmSession, title_id: UUID) -> Sequence[Account]:
    """Get the accounts explicitly granted upload access to a title."""
    return session.scalars(
        select(Account)
        .join(TitlePermission, TitlePermission.account_id == Account.id)
        .where(TitlePermission.title_id == title_id)
        .order_by(Account.display_name)
    ).all()


def get_title_permission_or_none(
    session: OrmSession, title_id: UUID, account_id: UUID
) -> TitlePermission | None:
    """Get the permission of an account on a title if it exists."""
    return session.scalars(
        select(TitlePermission).where(
            TitlePermission.title_id == title_id,
            TitlePermission.account_id == account_id,
        )
    ).one_or_none()


def delete_title_permission(session: OrmSession, title_id: UUID, account_id: UUID):
    """Delete the permission of an account on a title"""
    session.execute(
        delete(TitlePermission).where(
            TitlePermission.title_id == title_id,
            TitlePermission.account_id == account_id,
        )
    )
