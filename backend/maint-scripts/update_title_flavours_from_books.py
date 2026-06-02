#!/usr/bin/env python3
# ruff: noqa: T201
"""This script sets the title flavours from the set of all books belonging to the title.

It also fixes books whose flavours start with an underscore.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.models import Book, Title
from cms_backend.db.title import get_title_by_id


def update_title_flavour(session: OrmSession, title: Title) -> tuple[bool, str]:
    if title.archived:
        logger.info(f"Skipping archived title {title.id} ({title.name})")
        return (False, "Title is archived")

    books = session.scalars(
        select(Book)
        .join(Title, Book.title_id == Title.id)
        .order_by(Book.flavour)
        .where(Book.flavour.isnot(None), Book.title_id == title.id)
    ).all()
    for book in books:
        if book.flavour and book.flavour.startswith("_"):
            new_flavour = book.flavour[1:]
            logger.info(
                f"Updated book {book.name} from {book.flavour} to {new_flavour}"
            )
            book.flavour = new_flavour
            session.add(book)

    flavours = {book.flavour for book in books if book.flavour is not None}
    title.flavours = list(flavours)
    session.add(title)
    session.flush()

    if not flavours:
        logger.info(
            f"No flavours found in books belonging to title {title.id} ({title.name})"
        )
        return (
            False,
            f"No flavours found in books belonging to title {title.id} ({title.name})",
        )

    logger.info(f"✓ Updated title {title.id} ({title.name}) flavours to {flavours}")
    return (True, "")


def main():

    with Session.begin() as session:
        title_ids = session.scalars(select(Title.id)).all()
        logger.info(f"Found {len(title_ids)} titles to process")
        nb_titles_updated = 0
        nb_titles_skipped = 0
        reasons: list[dict[str, Any]] = []

        for title_id in title_ids:
            title = get_title_by_id(session, title_id=title_id)
            processed, reason = update_title_flavour(session, title)
            if processed:
                nb_titles_updated += 1
            else:
                nb_titles_skipped += 1
                reasons.append({title.name: reason})

        logger.info(
            f"Updated {nb_titles_updated} title(s) metadata, skipped "
            f"{nb_titles_skipped} titles(s)"
        )

        if reasons:
            print("\nSkipped titles summary:")
            print("| Title Name | Reason |")
            print("|------------|--------|")
            for entry in reasons:
                for title_name, reason in entry.items():
                    print(f"| {title_name} | {reason} |")


if __name__ == "__main__":
    main()
