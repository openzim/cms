from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.publication import (
    advance_publication,
    fail_publication,
    get_publications_in_progress,
)


def advance_publications(session: OrmSession):
    """Advance every publication which is waiting on GitHub."""
    logger.info("Advancing publications in progress")
    publications = get_publications_in_progress(session)
    nb_advanced = 0
    for publication in publications:
        try:
            if advance_publication(publication):
                nb_advanced += 1
        except Exception as exc:
            logger.exception(f"Error while advancing publication {publication.id}")
            fail_publication(
                publication,
                f"Unexpected error while advancing publication: {exc!s}",
            )
        session.commit()

    logger.info(
        f"Advanced {nb_advanced} of {len(publications)} publication(s) in progress"
    )
