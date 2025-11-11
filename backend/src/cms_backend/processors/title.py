from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.book import create_book_location
from cms_backend.db.models import Book, Title, TitleWarehousePath
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

        name = book.name

        title.books.append(book)
        book.events.append(f"{getnow()}: book added to title {title.id}")
        title.events.append(f"{getnow()}: book {book.id} added to title")
        book.status = "processed"

        if name and title.name != name:
            title.events.append(f"{getnow()}: updating title name to {name}")
            title.name = name

        # Update title producer display fields from book
        if title.producer_display_name != book.producer_display_name:
            title.events.append(
                f"{getnow()}: updating title producer_display_name to "
                f"{book.producer_display_name}"
            )
            title.producer_display_name = book.producer_display_name

        if title.producer_display_url != book.producer_display_url:
            title.events.append(
                f"{getnow()}: updating title producer_display_url to "
                f"{book.producer_display_url}"
            )
            title.producer_display_url = book.producer_display_url

        # Compute target filename once for this book
        target_filename = compute_target_filename(
            session,
            name=name,
            flavour=book.flavour,
            date=book.date,
        )

        # Determine which warehouse paths to use based on title.in_prod
        path_type = "prod" if title.in_prod else "dev"

        # Get all warehouse paths for this title and path_type
        stmt = select(TitleWarehousePath).where(
            TitleWarehousePath.title_id == title.id,
            TitleWarehousePath.path_type == path_type,
        )
        target_warehouse_paths = session.scalars(stmt).all()

        # Create target locations for each applicable warehouse path
        for title_warehouse_path in target_warehouse_paths:
            create_book_location(
                session=session,
                book=book,
                warehouse_path_id=title_warehouse_path.warehouse_path_id,
                filename=target_filename,
                status="target",
            )

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while adding to title {title.id}\n{exc}"
        )
        title.events.append(
            f"{getnow()}: error encountered while adding book {book.id}\n{exc}"
        )
        book.status = "errored"
        logger.exception(f"Failed to add book {book.id} to title {title.id}")
