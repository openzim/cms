#!/usr/bin/env python3
"""Maintenance script to create initial history entries for all existing collections.

This script:
- Creates a history entry for all collections that don't have any history yet
- Uses the 'maint-scripts' user as the author

"""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.account import get_account_by_username
from cms_backend.db.collection import create_collection_history_entry, get_collection
from cms_backend.db.models import Collection, CollectionHistory


def create_initial_history_for_collections(session: OrmSession) -> None:
    """Create initial history entries for all collections without history."""
    maint_user = get_account_by_username(session, username="maint-scripts")
    collection_ids = session.scalars(select(Collection.id)).all()
    logger.info(f"Found {len(collection_ids)} collection(s) in the database")

    created_count = 0
    skipped_count = 0

    for collection_id in collection_ids:
        existing_history = session.scalars(
            select(CollectionHistory).where(
                CollectionHistory.collection_id == collection_id
            )
        ).first()

        if existing_history:
            logger.info(f"Collection '{collection_id}) already has history, skipping")
            skipped_count += 1
            continue

        collection = get_collection(session, str(collection_id))

        create_collection_history_entry(
            session,
            collection=collection,
            author_id=maint_user.id,
            comment="Initial history entry created by maintenance script",
        )
        logger.info(f"Created initial history entry for collection '{collection_id}'")
        created_count += 1

    session.flush()

    logger.info(
        f"History creation complete: {created_count} created, {skipped_count} skipped"
    )


def main():

    with Session.begin() as session:
        create_initial_history_for_collections(session)


if __name__ == "__main__":
    main()
