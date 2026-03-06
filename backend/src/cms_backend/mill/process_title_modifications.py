from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.event import delete_event, get_next_event_to_process_or_none
from cms_backend.db.models import Book
from cms_backend.db.title import get_title_by_id_or_none
from cms_backend.mill.processors.book import process_book
from cms_backend.utils.zim import get_missing_keys


def process_title_modifications(session: OrmSession):
    logger.info("Processing title modification events")
    nb_events_processed = 0
    while True:
        event = get_next_event_to_process_or_none(session, topic="title_modified")
        if not event:
            break
        logger.debug(f"Processing title modification event {event.id}")

        missing_keys = get_missing_keys(event.payload, "id", "name", "action")
        if missing_keys:
            logger.warning(
                "Title modification event is missing mandatory keys: "
                f"{','.join(missing_keys)}"
            )
            delete_event(session, event_id=event.id)
            continue

        title = get_title_by_id_or_none(session, title_id=UUID(event.payload["id"]))
        if not title:
            logger.warning(f"Title with ID {event.payload['id']} does not exist.")
            delete_event(session, event_id=event.id)
            continue

        title_name = event.payload["name"]
        books_without_title = session.scalars(
            select(Book)
            .where(
                Book.title_id.is_(None),
                Book.has_error.is_(False),
                Book.name == title_name,
            )
            .order_by(Book.created_at)
        ).all()

        if not books_without_title:
            logger.info(f"No books without title matching title '{title_name}'")
            delete_event(session, event_id=event.id)
            continue

        logger.info(
            f"Found {len(books_without_title)} book(s) matching title '{title_name}'"
        )

        for book in books_without_title:
            with session.begin_nested():
                try:
                    process_book(session, book)
                except Exception:
                    logger.exception("error while processing book")
                else:
                    delete_event(session, event.id)
                    nb_events_processed += 1

    logger.info(f"Done processing {nb_events_processed} title modification events.")
