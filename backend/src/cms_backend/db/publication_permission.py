from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import account as db_account
from cms_backend.db import count_from_stmt
from cms_backend.db.models import Account, PublicationPermission
from cms_backend.roles import RoleEnum
from cms_backend.schemas.orms import AccountSchema, ListResult


def can_publish(session: OrmSession, account: Account, title_id: UUID) -> bool:
    """Whether an account may publish applications of a title.

    - Admins and global editors may publish any title
    - collection editors need an explicit grant for the title.
    """
    role = RoleEnum(account.role)
    if role in (RoleEnum.ADMIN, RoleEnum.GLOBAL_EDITOR):
        return True
    if role != RoleEnum.COLLECTION_EDITOR:
        return False
    return get_publication_permission_or_none(session, title_id, account.id) is not None


def create_publication_permission(
    session: OrmSession, title_id: UUID, account_id: UUID
) -> None:
    """Grant publishing rights on a title to an account."""
    permission = PublicationPermission(title_id=title_id, account_id=account_id)
    session.add(permission)
    session.flush()


def delete_publication_permissions(session: OrmSession, account_id: UUID) -> None:
    """Delete all publication permissions of an account."""
    session.execute(
        delete(PublicationPermission).where(
            PublicationPermission.account_id == account_id
        )
    )


def get_publication_publishers(
    session: OrmSession, title_id: UUID
) -> Sequence[Account]:
    """Get the accounts explicitly granted publishing rights on a title."""
    return session.scalars(
        select(Account)
        .join(PublicationPermission, PublicationPermission.account_id == Account.id)
        .where(PublicationPermission.title_id == title_id)
        .order_by(Account.display_name)
    ).all()


def get_available_publication_publishers(
    session: OrmSession, title_id: UUID, *, skip: int, limit: int
) -> ListResult[AccountSchema]:
    """Get collection-editor accounts not yet granted publishing rights."""
    stmt = (
        select(Account)
        .where(
            Account.deleted.is_(False),
            Account.role == RoleEnum.COLLECTION_EDITOR,
            ~exists().where(
                PublicationPermission.title_id == title_id,
                PublicationPermission.account_id == Account.id,
            ),
        )
        .order_by(Account.display_name, Account.id)
    )
    return ListResult[AccountSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            db_account.create_account_schema(account)
            for account in session.scalars(stmt.offset(skip).limit(limit)).all()
        ],
    )


def get_publication_permission_or_none(
    session: OrmSession, title_id: UUID, account_id: UUID
) -> PublicationPermission | None:
    """Get the publishing permission of an account on a title if it exists."""
    return session.scalars(
        select(PublicationPermission).where(
            PublicationPermission.title_id == title_id,
            PublicationPermission.account_id == account_id,
        )
    ).one_or_none()


def delete_publication_permission(
    session: OrmSession, title_id: UUID, account_id: UUID
) -> None:
    """Revoke the publishing permission of an account on a title."""
    session.execute(
        delete(PublicationPermission).where(
            PublicationPermission.title_id == title_id,
            PublicationPermission.account_id == account_id,
        )
    )
