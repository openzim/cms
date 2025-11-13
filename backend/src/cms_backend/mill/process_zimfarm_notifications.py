from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.db.zimfarm_notification import get_next_notification_to_process_or_none
from cms_backend.processors.zimfarm_notification import process_notification


def process_zimfarm_notifications(session: OrmSession):
    logger.info("Processing Zimfarm notifications")
    nb_notifications_processed = 0
    while True:
        with session.begin_nested():
            notification = get_next_notification_to_process_or_none(session)
            if not notification:
                break
            logger.debug(f"Processing Zimfarm notification {notification.id}")
            process_notification(session, notification)
            nb_notifications_processed += 1

    logger.info(f"Done processing {nb_notifications_processed} Zimfarm notifications")
