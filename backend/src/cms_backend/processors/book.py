from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.models import Book, Title
from cms_backend.db.title import get_title_by_name_and_producer_or_none
from cms_backend.utils.datetime import getnow


def check_book_qa(book: Book) -> bool:
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
            if key not in book.zim_metadata
        ]

        if missing_metadata_keys:
            book.events.append(
                f"{getnow()}: book is missing mandatory metadata: "
                f"{','.join(missing_metadata_keys)}"
            )
            book.status = "qa_failed"
            return False

        book.events.append(f"{getnow()}: book passed QA checks")
        return True

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while checking book QA\n{exc}"
        )
        logger.exception(f"Failed to check book QA for {book.id}")
        book.status = "errored"
        return False


def get_matching_title(session: ORMSession, book: Book) -> Title | None:
    try:
        name = str(book.zim_metadata.get("Name"))
        if not name:
            book.events.append(
                f"{getnow()}: no title can be found because name is missing"
            )
            book.status = "qa_failed"
            return None

        title = get_title_by_name_and_producer_or_none(
            session, name=name, producer_unique_id=book.producer_unique_id
        )

        if not title:
            book.events.append(f"{getnow()}: no matching title found for book")
            book.status = "pending_title"
            return None

        book.events.append(f"{getnow()}: found matching title {title.id}")
        return title

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while get matching title\n{exc}"
        )
        logger.exception(f"Failed to get matching title for {book.id}")
        book.status = "errored"
        return None
