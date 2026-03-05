from sqlalchemy import select
from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.models import Book, Title
from cms_backend.mill.processors.book import process_book


def process_title_modification(session: ORMSession, title: Title):
    """Process books without titles when a title is created or modified.

    When a title is created or when a title name is changed, we need to also
    automatically process books without titles attached, looking for potential
    new title/book match.
    """
    books_without_title = session.scalars(
        select(Book)
        .where(
            Book.title_id.is_(None), Book.has_error.is_(False), Book.name == title.name
        )
        .order_by(Book.created_at)
    ).all()

    if not books_without_title:
        logger.info(f"No books without title matching title '{title.name}'")
        return

    logger.info(
        f"Found {len(books_without_title)} book(s) matching title '{title.name}'"
    )

    for book in books_without_title:
        process_book(session, book)

    logger.info(f"Completed processing books without title for title '{title.name}' ")
