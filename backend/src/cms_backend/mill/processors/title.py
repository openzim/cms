from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db.book import create_book_target_locations
from cms_backend.db.models import Book, Title
from cms_backend.db.title import apply_retention_rules
from cms_backend.schemas.models import FileLocation
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
        target_filename = compute_target_filename(
            session,
            name=book.name,
            flavour=book.flavour,
            date=book.date,
            book_id=book.id,
        )

        # Determine if this book goes to staging or prod based on title maturity
        # For now, only 'robust' maturity move straight to prod, other maturity moves
        # through staging first
        goes_to_staging = title.maturity != "robust"

        target_locations = (
            [
                FileLocation(
                    Context.staging_warehouse_id,
                    Context.staging_base_path,
                    target_filename,
                )
            ]
            if goes_to_staging
            else [
                FileLocation(tc.collection.warehouse_id, tc.path, target_filename)
                for tc in title.collections
            ]
        )

        # Create target locations if not already at expected locations
        create_book_target_locations(
            session=session,
            book=book,
            target_locations=target_locations,
        )
        book.location_kind = "staging" if goes_to_staging else "prod"

        if not goes_to_staging:
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
