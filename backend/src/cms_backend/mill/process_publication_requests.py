from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.event import (
    PUBLICATION_REQUESTED_TOPIC,
    delete_event,
    get_next_event_to_process_or_none,
)
from cms_backend.db.publication import (
    fail_publication,
    get_publication_or_none,
    start_publication,
)
from cms_backend.utils.zim import get_missing_keys


def process_publication_requests(session: OrmSession):
    """Start publications queued by the API."""
    logger.info("Processing publication request events")
    nb_processed = 0
    while True:
        event = get_next_event_to_process_or_none(
            session, topic=PUBLICATION_REQUESTED_TOPIC
        )
        if not event:
            break

        missing_keys = get_missing_keys(event.payload, "id")
        if missing_keys:
            logger.warning(
                "Publication request event is missing mandatory keys: "
                f"{','.join(missing_keys)}"
            )
            delete_event(session, event_id=event.id)
            session.commit()
            continue

        publication_id = UUID(event.payload["id"])

        publication = get_publication_or_none(session, publication_id=publication_id)

        if publication is None:
            logger.warning(f"Publication {publication_id} does not exist.")
            delete_event(session, event_id=event.id)
            session.commit()
            continue

        try:
            start_publication(publication)
        except Exception:
            logger.exception(f"Error while starting publication {publication_id}")
            fail_publication(publication, "Unexpected error while starting publication")

        delete_event(session, event_id=event.id)
        session.commit()
        nb_processed += 1

    logger.info(f"Done processing {nb_processed} publication request events.")
