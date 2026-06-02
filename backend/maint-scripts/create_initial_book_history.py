#!/usr/bin/env python3
"""Maintenance script to create initial history entries for all existing books.

This script:
- Creates a history entry for all books that don't have any history yet
- Uses the 'maint-scripts' user as the author

"""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.account import get_account_by_username
from cms_backend.db.book import create_book_history_entry, get_book
from cms_backend.db.models import Book, BookHistory


def create_initial_history_for_books(session: OrmSession) -> None:
    """Create initial history entries for all books without history."""
    maint_user = get_account_by_username(session, username="maint-scripts")
    book_ids = session.scalars(select(Book.id)).all()
    logger.info(f"Found {len(book_ids)} book(s) in the database")

    created_count = 0
    skipped_count = 0

    for book_id in book_ids:
        existing_history = session.scalars(
            select(BookHistory).where(BookHistory.book_id == book_id)
        ).first()

        if existing_history:
            logger.info(f"Book '{book_id}) already has history, skipping")
            skipped_count += 1
            continue

        book = get_book(session, book_id)

        create_book_history_entry(
            session,
            book=book,
            author_id=maint_user.id,
            comment="Initial history entry created by maintenance script",
        )
        logger.info(f"Created initial history entry for book '{book_id}'")
        created_count += 1

    session.flush()

    logger.info(
        f"History creation complete: {created_count} created, {skipped_count} skipped"
    )


def main():

    with Session.begin() as session:
        create_initial_history_for_books(session)


if __name__ == "__main__":
    main()
