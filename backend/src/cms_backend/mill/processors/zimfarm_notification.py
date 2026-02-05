from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.book import create_book, create_book_location
from cms_backend.db.models import ZimfarmNotification
from cms_backend.mill.context import Context as MillContext
from cms_backend.mill.processors.book import process_book
from cms_backend.utils.datetime import getnow


def process_notification(session: ORMSession, notification: ZimfarmNotification):
    """Process a Zimfarm notification to update CMS

    - check all mandatory fields are present in notification
    - create a book
    - check book matches ZIM specification requirements
    - associate book with matching title if it already exists
    - move book from quarantine to staging
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
                "folder_name",
                "filename",
            ]
            if key not in notification.content
        ]

        if missing_notification_keys:
            notification.events.append(
                f"{getnow()}: notification is missing mandatory keys: "
                f"{','.join(missing_notification_keys)}"
            )
            notification.status = "bad_notification"
            return

        folder_name = notification.content.get("folder_name")
        filename = notification.content.get("filename")

        # Validate filename is a non-empty string
        if not isinstance(filename, str) or not filename:
            notification.events.append(
                f"{getnow()}: filename must be a non-empty string, got "
                f"{type(filename).__name__}: {filename}"
            )
            notification.status = "bad_notification"
            return

        # Validate folder_name is a string (can be empty for files at quarantine root)
        if not isinstance(folder_name, str):
            notification.events.append(
                f"{getnow()}: folder_name must be a string, got "
                f"{type(folder_name).__name__}: {folder_name}"
            )
            notification.status = "bad_notification"
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

        # Create current book location
        create_book_location(
            session=session,
            book=book,
            warehouse_id=MillContext.quarantine_warehouse_id,
            path=MillContext.quarantine_base_path / folder_name,
            filename=filename,
            status="current",
        )

        notification.status = "processed"

        # Try to move book to staging
        process_book(session, book)

    except Exception as exc:
        notification.events.append(
            f"{getnow()}: error encountered while processing notification\n{exc}"
        )
        logger.exception(f"Failed to process zimfarm notification {notification.id}")
        notification.status = "errored"
