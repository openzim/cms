from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.app_build import (
    fail_app_build,
    get_app_builds_to_process,
    process_app_build,
)


def process_app_builds(session: OrmSession):
    """Process every app build waiting for work."""
    logger.info("Processing app builds")
    builds = get_app_builds_to_process(session)
    nb_processed = 0
    for build in builds:
        try:
            if process_app_build(build):
                nb_processed += 1
        except Exception as exc:
            logger.exception(f"Error while processing build {build.id}")
            fail_app_build(
                build,
                f"Unexpected error while processing build: {exc!s}",
            )
        session.commit()

    logger.info(f"Processed {nb_processed} of {len(builds)} build(s)")
