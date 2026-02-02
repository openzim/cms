from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.models import Book, Title
from cms_backend.db.title import get_title_by_name_or_none
from cms_backend.mill.processors.title import add_book_to_title
from cms_backend.utils.datetime import getnow


def process_book(session: ORMSession, book: Book):
    try:
        if not check_book_zim_spec(book):
            return

        title = get_matching_title(session, book)

        if not title:
            return

        add_book_to_title(session, book, title)

    finally:
        book.needs_processing = False


def check_book_zim_spec(book: Book) -> bool:
    try:
        missing_metadata_keys = [
            key
            for key in sorted(
                [
                    "Name",
                    "Title",
                    "Creator",
                    "Publisher",
                    "Date",
                    "Description",
                    "Language",
                ]
            )
            if key not in book.zim_metadata or not book.zim_metadata.get(key)
        ]

        if missing_metadata_keys:
            book.events.append(
                f"{getnow()}: book is missing mandatory metadata: "
                f"{','.join(missing_metadata_keys)}"
            )
            book.has_error = True
            return False

        book.events.append(f"{getnow()}: book passed ZIM specification checks")
        return True

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while checking ZIM specification\n{exc}"
        )
        logger.exception(f"Failed to check ZIM specification for book {book.id}")
        book.has_error = True
        return False


def get_matching_title(session: ORMSession, book: Book) -> Title | None:
    try:
        if not book.name:
            book.events.append(
                f"{getnow()}: no title can be found because name is missing"
            )
            book.has_error = True
            return None

        title = get_title_by_name_or_none(session, name=book.name)

        if not title:
            book.events.append(f"{getnow()}: no matching title found for book")
            # Set all flags to False for pending_title state (passive wait)
            book.needs_processing = False
            book.has_error = False
            book.needs_file_operation = False
            return None

        book.events.append(f"{getnow()}: found matching title {title.id}")
        return title

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while get matching title\n{exc}"
        )
        logger.exception(f"Failed to get matching title for {book.id}")
        book.has_error = True
        return None
