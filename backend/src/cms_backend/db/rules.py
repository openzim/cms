import datetime
from collections import defaultdict
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db.models import Book, Title
from cms_backend.utils.datetime import getnow
from cms_backend.utils.filename import (
    PERIOD_LENGTH,
    get_period_and_suffix_from_filename,
)


def sort_books_by_filename_period(books: list[Book]) -> list[Book]:
    """Sort a list of books by period.

    Assumes:
    - the book's location exists since it contains the filename of the book
    """

    def sort_fn(book: Book) -> tuple[str, int, str]:
        period, suffix = get_period_and_suffix_from_filename(book.locations[0].filename)
        return (period, len(suffix), suffix)

    return sorted(
        books,
        key=sort_fn,
        reverse=True,
    )


def apply_retention_rules(session: OrmSession, title: Title):
    """Apply retention rules to `prod` books belonging to same title and flavour group.

    The retention rules are described in https://wiki.openzim.org/wiki/ZIM_Updates
    - Keep last version of two ZIM files from the two last distinct months (e.g
        if we have `2024-04`, `2024-04a`, `2024-06`, `2024-06a`, `2024-06b`,
        then we keep `2024-04a` and `2024-06b`)
    - AND keep every version which is 30 days old or less.
    """

    now = getnow()
    thirty_days_ago = (now - datetime.timedelta(days=30)).date()

    books_by_flavour: dict[str, list[Book]] = defaultdict(list)
    for book in session.scalars(
        select(Book).where(
            Book.title_id == title.id,
            Book.has_error.is_(False),
            Book.date.is_not(None),
            Book.location_kind == "prod",
            Book.needs_file_operation.is_(False),
        )
    ).all():
        books_by_flavour[book.flavour or ""].append(book)

    books_to_delete: list[Book] = []

    for _, books in books_by_flavour.items():
        # Group books by period (without the suffix)
        books_by_period: dict[str, list[Book]] = defaultdict(list)
        for book in books:
            books_by_period[cast(str, book.date)[:PERIOD_LENGTH]].append(book)

        sorted_periods = sorted(books_by_period.keys(), reverse=True)
        # Keep latest version from each of the 2 most recent periods
        books_to_keep: set[UUID] = set()

        for period in sorted_periods[:2]:
            sorted_books_by_period = sort_books_by_filename_period(
                books_by_period[period]
            )
            books_to_keep.add(sorted_books_by_period[0].id)

        for book in books:
            book_date = datetime.date.fromisoformat(cast(str, book.date))
            if book_date <= thirty_days_ago and book.id not in books_to_keep:
                books_to_delete.append(book)

    deletion_date = now + Context.book_deletion_delay

    for book in books_to_delete:
        logger.info(
            f"Marking book {book.id} for deletion, deletion_date={deletion_date}"
        )
        book.location_kind = "to_delete"
        book.deletion_date = deletion_date
        book.needs_file_operation = True
        book.events.append(
            f"{now}: marked for deletion due to retention policy, "
            f"will be deleted after {deletion_date}"
        )
        title.events.append(f"{now}: book {book.id} marked for deletion.")
        session.add(book)
        session.add(title)

    session.flush()


def title_is_missing_mandatory_metadata(title: Title) -> bool:
    """Check if a title is missing the mandatory metadata information

    See https://wiki.openzim.org/wiki/Metadata for the list of metadata
    """

    return any(
        value is None
        for value in [
            title.title,
            title.creator,
            title.publisher,
            title.description,
            title.language,
            title.illustration_48x48_at_1,
        ]
    )
