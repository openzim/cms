from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session as ORMSession

from cms_backend import logger
from cms_backend.db.book import create_book, create_book_location
from cms_backend.db.models import Warehouse, WarehousePath, ZimfarmNotification
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
                "warehouse_name",
                "folder_name",
                "filename",
                "producer",
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

        # Validate producer information
        producer = notification.content.get("producer")
        if not isinstance(producer, dict) or not all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in producer.items()  # pyright: ignore[reportUnknownVariableType]
        ):
            notification.events.append(f"{getnow()}: producer must be a dict[str, str]")
            notification.status = "bad_notification"
            return
        else:
            producer = cast(dict[str, str], producer)

        missing_producer_keys = [
            key
            for key in ["displayName", "displayUrl", "uniqueId"]
            if key not in producer
        ]

        if missing_producer_keys:
            notification.events.append(
                f"{getnow()}: producer is missing mandatory keys: "
                f"{','.join(missing_producer_keys)}"
            )
            notification.status = "bad_notification"
            return

        # Look up warehouse path by warehouse_name and folder_name
        warehouse_name = notification.content.get("warehouse_name")
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

        stmt = (
            select(WarehousePath)
            .join(Warehouse)
            .where(
                Warehouse.name == warehouse_name,
                WarehousePath.folder_name == folder_name,
            )
        )
        warehouse_path = session.scalars(stmt).one_or_none()

        if not warehouse_path:
            notification.events.append(
                f"{getnow()}: warehouse path not found: {warehouse_name}/{folder_name}"
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
            producer_display_name=producer["displayName"],
            producer_display_url=producer["displayUrl"],
            producer_unique_id=producer["uniqueId"],
        )

        # Create current book location
        create_book_location(
            session=session,
            book=book,
            warehouse_path_id=warehouse_path.id,
            filename=filename,
            status="current",
        )

        notification.status = "processed"

        if not check_book_qa(book):
            return

        title = get_matching_title(session, book)

        if not title:
            return

        add_book_to_title(session, book, title)

    except Exception as exc:
        notification.events.append(
            f"{getnow()}: error encountered while processing notification\n{exc}"
        )
        logger.exception(f"Failed to process zimfarm notification {notification.id}")
        notification.status = "errored"
