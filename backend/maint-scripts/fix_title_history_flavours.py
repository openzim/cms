#!/usr/bin/env python3
"""Maintenance script to fix title history entries whose flavours are outdated."""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.account import get_account_by_username
from cms_backend.db.models import Title, TitleHistory
from cms_backend.db.title import create_title_history_entry, get_title_by_id


def get_current_flavours(title: Title) -> set[tuple[str, str | None]]:
    """Return a title's current flavours as (flavour, recipe_id) pairs."""
    return {
        (tf.flavour, str(tf.recipe_id) if tf.recipe_id else None)
        for tf in title.flavours
    }


def get_history_flavours(entry: TitleHistory) -> set[tuple[str, str | None]]:
    """Return the flavours of a history entry as (flavour, recipe_id) pairs."""
    return {(tf["flavour"], tf.get("recipe_id")) for tf in entry.flavours}


def fix_title_history_flavours(session: OrmSession) -> None:
    """Create a history entry for titles whose latest one has outdated flavours."""
    maint_user = get_account_by_username(session, username="maint-scripts")
    title_ids = session.scalars(select(Title.id)).all()
    logger.info(f"Found {len(title_ids)} title(s) in the database")

    created_count = 0
    skipped_count = 0

    for title_id in title_ids:
        title = get_title_by_id(session, title_id=title_id)
        current_flavours = get_current_flavours(title)
        latest_entry = title.history_entries[0] if title.history_entries else None

        if (
            latest_entry is not None
            and get_history_flavours(latest_entry) == current_flavours
        ):
            logger.debug(
                f"Title '{title.name}' (ID: {title.id}) history already matches "
                "its current flavours, skipping"
            )
            skipped_count += 1
            continue

        create_title_history_entry(
            session,
            title=title,
            author_id=maint_user.id,
            comment=(
                "History entry created by maintenance script to reflect the "
                "current "
                "flavours configuration"
            ),
        )
        flavours = ", ".join(sorted(tf.flavour for tf in title.flavours)) or "none"
        logger.info(
            f"Created history entry for title '{title.name}' (ID: {title.id}) "
            f"with flavours: {flavours}"
        )
        created_count += 1

    session.flush()

    logger.info(
        f"Flavours history fix complete: {created_count} created, "
        f"{skipped_count} skipped"
    )


def main():

    with Session.begin() as session:
        fix_title_history_flavours(session)


if __name__ == "__main__":
    main()
