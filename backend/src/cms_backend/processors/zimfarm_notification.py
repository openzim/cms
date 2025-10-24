from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.book import create_book
from cms_backend.db.models import ZimfarmNotification
from cms_backend.processors.book import check_book_qa, get_matching_title
from cms_backend.processors.title import add_book_to_title
from cms_backend.utils.datetime import getnow


def process_notification(session: ORMSession, notification: ZimfarmNotification):
    """Process a Zimfarm notification to update CMS

    - check all mandatory fields are present in notification
    - create a book
    - check book for QA rules
    - associate book with matching title if it already exists
    """
    try:
        missing_notification_keys = [
            key
            for key in [
                "article_count",
                "media_count",
                "size",
                "metadata",
                "zimcheck",
                "url",
            ]
            if key not in notification.content
        ]

        if missing_notification_keys:
            notification.events.append(
                f"{getnow()}: notification is missing mandatory keys: "
                f"{','.join(missing_notification_keys)}"
            )
            return

        book = create_book(
            session=session,
            book_id=notification.id,
            article_count=notification.content["article_count"],
            media_count=notification.content["media_count"],
            size=notification.content["size"],
            zim_metadata=notification.content["metadata"],
            zimcheck_result=notification.content["zimcheck"],
            zimfarm_notification=notification,
        )

        if not check_book_qa(book):
            return

        title = get_matching_title(session, book)

        if not title:
            return

        add_book_to_title(book, title)

    except Exception as exc:
        notification.events.append(
            f"{getnow()}: error encountered while processing notification\n{exc}"
        )
        logger.exception(f"Failed to process zimfarm notification {notification.id}")
        notification.errored = True
    finally:
        notification.processed = True
