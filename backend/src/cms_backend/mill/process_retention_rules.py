from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.models import Title
from cms_backend.mill.processors.title import apply_retention_rules


def process_retention_rules(session: OrmSession):
    logger.info("Applying retention rules to all titles")
    nb_titles_processed = 0

    titles = session.scalars(select(Title)).all()

    for title in titles:
        with session.begin_nested():
            try:
                apply_retention_rules(session, title)
            except Exception:
                logger.exception(
                    f"Error while applying retention rules to title {title.id}"
                )
            else:
                nb_titles_processed += 1

    logger.info(f"Done applying retention rules to {nb_titles_processed} titles.")
