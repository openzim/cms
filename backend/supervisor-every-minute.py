#!/usr/bin/env python3

import logging

from cms_backend.db import Session
from cms_backend.db.zimfarm_notification import get_next_notification_to_process_or_none
from cms_backend.processors.zimfarm_notification import process_notification

# constants
NAME = "every-minute"

logger = logging.getLogger(NAME)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("[%(name)s - %(asctime)s: %(levelname)s] %(message)s")
)
logger.addHandler(handler)


def process_zimfarm_notifications():
    logger.info("Processing Zimfarm notifications")
    nb_notifications_processed = 0
    while True:
        with Session.begin() as session:
            notification = get_next_notification_to_process_or_none(session)
            if not notification:
                break
            logger.debug(f"Processing Zimfarm notification {notification.id}")
            process_notification(session, notification)
            nb_notifications_processed += 1

    logger.info(f"Done processing {nb_notifications_processed} Zimfarm notifications")


def main():
    logger.info(f"Starting {NAME} script")

    process_zimfarm_notifications()


if __name__ == "__main__":
    main()
