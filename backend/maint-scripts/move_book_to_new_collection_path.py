#!/usr/bin/env python3
"""Maintenance script to move prod book to new collection path in the same title.

NOTE:
- Books will be removed from existing collection paths and scheduled to be moved
to new collection path
- All
"""

import argparse
from pathlib import Path
from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.book import get_book_or_none
from cms_backend.db.book_location import create_book_target_locations
from cms_backend.db.collection import get_collection_by_name
from cms_backend.db.models import CollectionTitle, Title
from cms_backend.db.title import get_title
from cms_backend.schemas.models import FileLocation
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import compute_target_filename


def update_prod_book_locations(session: OrmSession, title: Title, exclude_book: UUID):
    prod_books = [
        book
        for book in title.books
        if book.location_kind == "prod" and book.id != exclude_book
    ]
    for book in prod_books:
        # Since book is already in prod, it should have at least one
        # current location
        if not book.locations:
            raise ValueError(
                f"Book {book.id} has location_kind='prod' but no locations"
            )

        current_location = next(
            (loc for loc in book.locations if loc.status == "current"),
            None,
        )
        if not current_location:
            raise ValueError(
                f"Book {book.id} has location_kind='prod' but no current location"
            )

        # Build new target locations based on updated collection_titles
        target_locations = [
            FileLocation(tc.collection.warehouse_id, tc.path, current_location.filename)
            for tc in title.collections
        ]

        for loc in list(book.locations):
            if loc.status == "target":
                session.delete(loc)

        create_book_target_locations(
            session=session,
            book=book,
            target_locations=target_locations,
        )

        book.events.append(
            f"{getnow()}: locations updated due to title collection change"
        )


def main(
    book_id: UUID,
    collection_name: str,
    collection_path: str,
    *,
    generate_new_filename: bool = False,
):
    with Session.begin() as session:
        book = get_book_or_none(
            session,
            book_id,
            locations=["prod"],
            needs_file_operation=False,
            needs_processing=False,
        )

        if book is None:
            logger.error(f"Book {book_id} does not exist")
            return

        if book.title_id is None:
            logger.error(f"Book {book_id} has no title.")
            return

        title = get_title(session, str(book.title_id))
        # Remove existing collection_titles
        for tc in title.collections:
            session.delete(tc)

        title.collections.clear()
        session.flush()

        collection = get_collection_by_name(session, collection_name)
        collection_title = CollectionTitle(path=Path(collection_path))
        collection_title.collection = collection
        collection_title.title = title
        session.add(collection_title)

        # update book locations for prod books for other books
        update_prod_book_locations(session, title, exclude_book=book.id)

        # update the current book separately as we might want to generate new filename
        current_location = next(
            (loc for loc in book.locations if loc.status == "current"), None
        )
        if not current_location:
            logger.error(f"Book {book.id} has no current location")
            return

        if generate_new_filename:
            filename = compute_target_filename(
                session,
                name=title.name,
                flavour=book.flavour,
                date=cast(str, book.date),
                book_id=book.id,
            )
            book.filename = filename
        else:
            filename = current_location.filename

        target_locations = [
            FileLocation(
                collection_title.collection.warehouse_id,
                collection_title.path,
                filename,
            )
        ]
        create_book_target_locations(
            session=session,
            book=book,
            target_locations=target_locations,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-process book")
    parser.add_argument(
        "--book", help="ID of book to process", type=UUID, required=True
    )
    parser.add_argument("--collection", help="Collection to add book", required=True)
    parser.add_argument("--path", help="Path in collection to add book", required=True)
    parser.add_argument(
        "--generate-new-filename",
        help="Generate new filename for book",
        action="store_true",
    )

    args = parser.parse_args()

    main(
        book_id=args.book,
        collection_name=args.collection,
        collection_path=args.path,
        generate_new_filename=args.generate_new_filename,
    )
