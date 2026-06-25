from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import delete_book
from cms_backend.db.books import get_books
from cms_backend.mill.context import Context as MillContext
from cms_backend.utils.datetime import getnow


def mark_staging_books_for_deletion(session: OrmSession):
    logger.info("Marking staging books that have exceeded lifespan for deletion")
    nb_books_marked = 0
    omit_book_ids: list[UUID] = []
    while True:
        results = get_books(
            session,
            needs_file_operation=False,
            needs_processing=False,
            created_before=getnow() - MillContext.staging_books_lifespan,
            skip=0,
            limit=50,
            location_kinds=["staging"],
            omit_book_ids=omit_book_ids,
        )
        if not results.records:
            break

        for book in results.records:
            omit_book_ids.append(book.id)
            try:
                delete_book(
                    session,
                    book_id=book.id,
                    deletion_delay=MillContext.staging_books_deletion_grace_period,
                )
            except Exception:
                logger.exception(f"error while marking book {book.id} for deletion")
            else:
                session.commit()
                nb_books_marked += 1

    logger.info(f"Done marking {nb_books_marked} staging book(s) for deletion")
