#!/usr/bin/env python3
"""Maintenance script to create initial history entries for all existing titles.

This script:
- Creates a history entry for all titles that don't have any history yet
- Uses the 'maint-scripts' user as the author

"""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.account import get_account_by_username
from cms_backend.db.models import Title, TitleHistory
from cms_backend.db.title import create_title_history_entry, get_title


def create_initial_history_for_titles(session: OrmSession) -> None:
    """Create initial history entries for all titles without history."""
    maint_user = get_account_by_username(session, username="maint-scripts")
    title_data = session.execute(select(Title.name, Title.id)).all()
    logger.info(f"Found {len(title_data)} title(s) in the database")

    created_count = 0
    skipped_count = 0

    for title_name, title_id in title_data:
        existing_history = session.scalars(
            select(TitleHistory).where(TitleHistory.title_id == title_id)
        ).first()

        if existing_history:
            logger.info(
                f"Title '{title_name}' (ID: {title_id}) already has history, skipping"
            )
            skipped_count += 1
            continue

        title = get_title(session, title_name)

        create_title_history_entry(
            session,
            title=title,
            author_id=maint_user.id,
            comment="Initial history entry created by maintenance script",
        )
        logger.info(
            f"Created initial history entry for title '{title.name}' (ID: {title.id})"
        )
        created_count += 1

    session.flush()

    logger.info(
        f"History creation complete: {created_count} created, {skipped_count} skipped"
    )


def main():

    with Session.begin() as session:
        create_initial_history_for_titles(session)


if __name__ == "__main__":
    main()
