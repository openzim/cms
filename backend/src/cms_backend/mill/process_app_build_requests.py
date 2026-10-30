from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.app_build import (
    fail_app_build,
    get_app_build_or_none,
    start_app_build,
)
from cms_backend.db.event import (
    APP_BUILD_REQUESTED_TOPIC,
    delete_event,
    get_next_event_to_process_or_none,
)
from cms_backend.utils.zim import get_missing_keys


def process_app_build_requests(session: OrmSession):
    """Start builds queued by the API."""
    logger.info("Processing build request events")
    nb_processed = 0
    while True:
        event = get_next_event_to_process_or_none(
            session, topic=APP_BUILD_REQUESTED_TOPIC
        )
        if not event:
            break

        missing_keys = get_missing_keys(event.payload, "id")
        if missing_keys:
            logger.warning(
                "Build request event is missing mandatory keys: "
                f"{','.join(missing_keys)}"
            )
            delete_event(session, event_id=event.id)
            session.commit()
            continue

        build_id = UUID(event.payload["id"])

        build = get_app_build_or_none(session, build_id=build_id)

        if build is None:
            logger.warning(f"Build {build_id} does not exist.")
            delete_event(session, event_id=event.id)
            session.commit()
            continue

        try:
            start_app_build(build)
        except Exception:
            logger.exception(f"Error while starting build {build_id}")
            fail_app_build(build, "Unexpected error while starting build")

        delete_event(session, event_id=event.id)
        session.commit()
        nb_processed += 1

    logger.info(f"Done processing {nb_processed} build request events.")
