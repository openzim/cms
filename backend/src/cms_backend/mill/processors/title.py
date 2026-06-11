from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import (
    process_book,
)
from cms_backend.db.models import Book, Title
from cms_backend.db.rules import (
    apply_retention_rules,
    title_is_missing_mandatory_metadata,
)
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import compute_target_filename


def add_book_to_title(session: OrmSession, book: Book, title: Title):
    try:
        # Retrieve name from book.name directly
        if not book.name:
            raise Exception("book name is missing or invalid")

        # Validate book.date is also present and valid
        if not book.date:
            raise Exception("book date is missing or invalid")

        title.books.append(book)
        book.events.append(f"{getnow()}: book added to title {title.id}")
        title.events.append(f"{getnow()}: book {book.id} added to title")

        # Update title name should it have changed (e.g. stackexchange domain updated
        # leading to ZIM name automatically updated as well)
        if title.name != book.name:
            title.events.append(f"{getnow()}: updating title name to {book.name}")
            title.name = book.name

        # Compute target filename once for this book
        book.filename = compute_target_filename(
            session,
            name=book.name,
            flavour=book.flavour,
            date=book.date,
            book_id=book.id,
        )

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

        process_book(session, book, update_events=True)
        if book.location_kind == "prod":
            apply_retention_rules(session, title)

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while adding to title {title.id}\n{exc}"
        )
        title.events.append(
            f"{getnow()}: error encountered while adding book {book.id}\n{exc}"
        )
        book.has_error = True
        logger.exception(f"Failed to add book {book.id} to title {title.id}")
