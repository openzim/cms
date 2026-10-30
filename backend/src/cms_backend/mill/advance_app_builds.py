from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.app_build import (
    advance_app_build,
    fail_app_build,
    get_app_builds_in_progress,
)


def advance_app_builds(session: OrmSession):
    """Advance every build which is waiting on GitHub."""
    logger.info("Advancing builds in progress")
    builds = get_app_builds_in_progress(session)
    nb_advanced = 0
    for build in builds:
        try:
            if advance_app_build(build):
                nb_advanced += 1
        except Exception as exc:
            logger.exception(f"Error while advancing build {build.id}")
            fail_app_build(
                build,
                f"Unexpected error while advancing build: {exc!s}",
            )
        session.commit()

    logger.info(f"Advanced {nb_advanced} of {len(builds)} build(s) in progress")
