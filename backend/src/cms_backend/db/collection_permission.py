from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Account, Collection, CollectionPermission
from cms_backend.roles import RoleEnum


def get_accessible_collection_ids(
    session: OrmSession, account: Account | None
) -> Sequence[UUID] | None:
    """Get the collection IDs account is allowed to operate on

    NOTE: None implies to skip check if account has permission to collection.
    This translates to account having access to all collections, books, titles, etc
    """
    if account and account.role == RoleEnum.COLLECTION_EDITOR:
        return session.scalars(
            select(Collection.id)
            .join(
                CollectionPermission,
                CollectionPermission.collection_id == Collection.id,
            )
            .where(CollectionPermission.account_id == account.id)
        ).all()


def create_collection_permission(
    session: OrmSession, collection_id: UUID, account_id: UUID
):
    """Create a collection permission for the current account on the collection"""
    permission = CollectionPermission(
        collection_id=collection_id, account_id=account_id
    )
    session.add(permission)
    session.flush()


def delete_collection_permissions(session: OrmSession, account_id: UUID):
    """Delete all collection permissions for account"""
    session.execute(
        delete(CollectionPermission).where(
            CollectionPermission.account_id == account_id
        )
    )
