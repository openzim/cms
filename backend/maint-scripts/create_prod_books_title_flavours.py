#!/usr/bin/env python3
"""Maintenance script to create title flavours for prod books that don't have any
title flavour associated with them.

This script is idempotent and can be run multiple times without creating duplicates.
"""

from sqlalchemy import and_, exists, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.flavour import create_title_flavour, get_title_flavour_or_none
from cms_backend.db.models import Book, BookLocation, TitleFlavour
from cms_backend.db.title import get_title_by_id


def main(session: OrmSession, *, dry_run: bool):

    stmt = (
        select(Book.title_id, Book.flavour, Book.recipe_id)
        .join(
            BookLocation,
            and_(
                BookLocation.book_id == Book.id,
                BookLocation.status == "current",
                BookLocation.is_backup.is_not(True),
            ),
        )
        .where(
            Book.location_kind == "prod",
            Book.title_id.is_not(None),
            Book.filename.is_not(None),
            ~exists().where(
                TitleFlavour.title_id == Book.title_id,
                TitleFlavour.flavour == Book.flavour,
            ),
        )
        .distinct(Book.title_id, Book.flavour)
        .order_by(Book.title_id, Book.flavour, Book.date.desc().nulls_last())
    )
    rows = session.execute(stmt).all()
    logger.info(
        f"Found {len(rows)} prod book flavour(s) without a matching title flavour"
    )

    nb_created = 0

    for title_id, flavour, recipe_id in rows:
        title = get_title_by_id(session, title_id=title_id)
        if get_title_flavour_or_none(session, title_id, flavour) is not None:
            continue

        if dry_run:
            logger.info(
                f"Would create title flavour '{flavour}' for title "
                f"{title.name} (recipe_id={recipe_id})"
            )
        else:
            create_title_flavour(session, title, recipe_id, flavour)
            logger.info(
                f"Created title flavour '{flavour}' for title '{title.name}' "
                f"(recipe_id={recipe_id})"
            )
        nb_created += 1

    logger.info(
        f"Missing title flavour fix complete: {nb_created} "
        f"{'would be ' if dry_run else ''}created"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Create title flavours for prod books tthat don't have any "
            "associated title flavour."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not commit changes to the database",
    )
    args = parser.parse_args()

    with Session.begin() as session:
        main(session, dry_run=args.dry_run)
