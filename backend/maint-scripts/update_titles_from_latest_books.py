#!/usr/bin/env python3
# ruff: noqa: T201

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.models import Book, Title
from cms_backend.db.rules import title_is_missing_mandatory_metadata
from cms_backend.db.title import get_title_by_id


def get_latest_book_for_title(session: OrmSession, title: Title) -> Book | None:
    """Get the latest prod/staging book for a title..

    Assumes book has passed all the checks done by the mill when it processes
    a zimfarm notification.
    """
    stmt = (
        select(Book)
        .where(
            Book.title_id == title.id,
            Book.location_kind.in_(["prod", "staging"]),
            Book.needs_processing.is_(False),
            Book.has_error.is_(False),
            Book.needs_file_operation.is_(False),
        )
        .order_by(
            # let prod books take precedence by sorting location_kind in ascending order
            Book.location_kind.asc(),
            Book.created_at.desc(),
        )
        .limit(1)
    )
    return session.scalars(stmt).first()


def process_title(session: OrmSession, title: Title) -> tuple[bool, str]:
    """Process a single title: fetch latest book and update metadata."""
    if title.archived:
        logger.info(f"Skipping archived title {title.id} ({title.name})")
        return (False, "Title is archived")

    book = get_latest_book_for_title(session, title)

    if not book:
        logger.info(f"No prod/staging books found for title {title.id} ({title.name})")
        return (False, "No prod/staging book found meet constraints")

    if title_is_missing_mandatory_metadata(title):
        title.title = book.zim_metadata["Title"]
        title.creator = book.zim_metadata["Creator"]
        title.publisher = book.zim_metadata["Publisher"]
        title.description = book.zim_metadata["Description"]
        title.language = book.zim_metadata["Language"]
        title.illustration_48x48_at_1 = book.zim_metadata["Illustration_48x48@1"]
        title.long_description = book.zim_metadata.get("LongDescription")
        title.license = book.zim_metadata.get("License")
        title.relation = book.zim_metadata.get("Relation")
        title.source = book.zim_metadata.get("Source")
        logger.info(f"✓ Updated title {title.id} ({title.name}) from book {book.id}")
        return (True, "")
    else:
        logger.info(f"No updates needed for title {title.id} ({title.name}) ")
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
            processed, reason = process_title(session, title)
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
