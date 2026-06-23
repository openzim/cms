from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import delete_book
from cms_backend.db.books import get_books
from cms_backend.mill.context import Context as MillContext
from cms_backend.utils.datetime import getnow


def mark_staging_books_for_deletion(session: OrmSession):
    logger.info("Marking staging books that have exceeded lifespan for deletion")
    nb_books_marked = 0
    skip = 0
    limit = 50
    while True:
        results = get_books(
            session,
            needs_file_operation=False,
            needs_processing=False,
            created_before=getnow() - MillContext.staging_books_lifespan,
            skip=skip,
            limit=limit,
            location_kinds=["staging"],
        )
        if not results.records:
            break

        for book in results.records:
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
        skip += limit

    logger.info(f"Done marking {nb_books_marked} staging book(s) for deletion")
