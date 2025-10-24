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

        if name and title.name != name:
            title.events.append(f"{getnow()}: updating title name to {name}")
            title.name = name

    except Exception as exc:
        book.events.append(
            f"{getnow()}: error encountered while adding to title {title.id}\n{exc}"
        )
        title.events.append(
            f"{getnow()}: error encountered while adding book {book.id}\n{exc}"
        )
        logger.exception(f"Failed to add book {book.id} to title {title.id}")
