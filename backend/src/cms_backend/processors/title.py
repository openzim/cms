from cms_backend import logger
from cms_backend.db.models import Book, Title
from cms_backend.utils.datetime import getnow


def add_book_to_title(book: Book, title: Title):
    try:
        name = book.zim_metadata.get("Name")
        if not name:
            raise Exception("book Name is missing")
        if not isinstance(name, str):
            raise Exception(f"book Name is expected to be a string, found {type(name)}")

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

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while adding to title {title.id}\n{exc}"
        )
        title.events.append(
            f"{getnow()}: error encountered while adding book {book.id}\n{exc}"
        )
        book.status = "errored"
        logger.exception(f"Failed to add book {book.id} to title {title.id}")
