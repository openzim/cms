import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import Book
from cms_backend.shuttle.context import Context as ShuttleContext
from cms_backend.utils.datetime import getnow


def delete_files(session: OrmSession):
    """Delete books from filesystem that have passed their deletion_date.

    Finds books with location_kind='to_delete' and deletion_date <= now,
    deletes their files from filesystem, and marks them as 'deleted'.
    """
    now = getnow()
    nb_zim_files_deleted = 0

    while True:
        with session.begin_nested():
            book = get_next_book_to_delete(session, now)
            if not book:
                break

            try:
                logger.debug(f"Deleting files for book {book.id}")
                delete_book_files(session, book)
                nb_zim_files_deleted += 1
            except Exception as exc:
                book.events.append(
                    f"{getnow()}: error encountered while deleting files\n{exc}"
                )
                logger.exception(f"Failed to delete files for book {book.id}")
                book.has_error = True

    logger.info(f"Done deleting {nb_zim_files_deleted} ZIM files")


def get_next_book_to_delete(session: OrmSession, now: datetime.datetime) -> Book | None:
    """Get the next book that needs deletion."""
    return session.scalars(
        select(Book)
        .where(
            Book.location_kind == "to_delete",
            Book.deletion_date <= now,
            Book.has_error.is_(False),
            Book.needs_file_operation.is_(True),
        )
        .order_by(Book.deletion_date)
        .limit(1)
    ).one_or_none()


def delete_book_files(session: OrmSession, book: Book):
    """Delete all files for a book from filesystem."""
    inaccessible_warehouse_names = {
        loc.warehouse.name
        for loc in book.locations
        if loc.warehouse_id not in ShuttleContext.local_warehouse_paths.keys()
    }

    # If any warehouse is not accessible, we cannot proceed
    if len(inaccessible_warehouse_names) > 0:
        logger.debug(
            f"Cannot delete book {book.id}, no access to "
            f"{','.join(inaccessible_warehouse_names)} warehouses"
        )
        return

    # Delete all current location files
    for location in book.locations:
        if location.status == "current":
            try:
                file_path = location.full_local_path(
                    ShuttleContext.local_warehouse_paths
                )
                file_path.unlink(missing_ok=True)
                logger.info(f"Deleted file for book {book.id} at {file_path}")
                book.events.append(f"{getnow()}: deleted file at {location.full_str}")
                session.delete(location)
            except Exception:
                logger.exception(
                    f"Failed to delete file at {location.full_str} for book {book.id}"
                )
                raise

    # Mark book as deleted
    book.location_kind = "deleted"
    book.needs_file_operation = False
    book.events.append(f"{getnow()}: all files deleted, book marked as deleted")
    session.add(book)

    session.flush()
    logger.info(f"Book {book.id} files have been deleted")
