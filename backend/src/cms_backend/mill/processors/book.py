from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.book import add_book_to_title
from cms_backend.db.models import Book, Title
from cms_backend.db.title import get_title_by_id, get_title_by_name_or_none
from cms_backend.db.title_upload import get_last_title_upload_for_recipe
from cms_backend.utils.datetime import getnow
from cms_backend.utils.zim import get_missing_metadata_keys


def process_book(session: ORMSession, book: Book):
    try:
        if not check_book_zim_spec(book):
            return

        title = get_matching_title(session, book)

        if not title:
            return

        if title.archived:
            book.events.append(
                f"{getnow()}: cannot add book to title because title is archived"
            )
            return

        add_book_to_title(session, book, title)

    finally:
        book.needs_processing = False


def check_book_zim_spec(book: Book) -> bool:
    try:
        if not book.article_count:
            book.events.append(f"{getnow()}: book has no article(s)")
            book.has_error = True
            return False

        missing_metadata_keys = get_missing_metadata_keys(book.zim_metadata)
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


def get_matching_title(
    session: ORMSession,
    book: Book,
    accessible_collection_ids: Sequence[UUID] | None = None,
) -> Title | None:
    try:
        if not book.name:
            book.events.append(
                f"{getnow()}: no title can be found because name is missing"
            )
            book.has_error = True
            return None

        # if a book is created from a manually uploaded zim, we want to attach book
        # to the title
        if book.recipe_id:
            title_upload = get_last_title_upload_for_recipe(session, book.recipe_id)
            if title_upload and title_upload.title_id:
                title = get_title_by_id(
                    session,
                    title_id=title_upload.title_id,
                    accessible_collection_ids=accessible_collection_ids,
                )
                book.events.append(
                    f"{getnow()}: found matching title {title.id} from requested "
                    "task {requested_task.id}"
                )
                return title

        title = get_title_by_name_or_none(
            session,
            name=book.name,
            accessible_collection_ids=accessible_collection_ids,
        )

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
