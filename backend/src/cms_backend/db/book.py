from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, ZimfarmNotification
from cms_backend.utils.datetime import getnow


def create_book(
    session: OrmSession,
    *,
    book_id: UUID,
    article_count: int,
    media_count: int,
    size: int,
    zim_metadata: dict[str, Any],
    zimcheck_result: dict[str, Any],
    zimfarm_notification: ZimfarmNotification,
) -> Book:
    """Create a new book"""

    book = Book(
        id=book_id,
        article_count=article_count,
        media_count=media_count,
        size=size,
        zim_metadata=zim_metadata,
        zimcheck_result=zimcheck_result,
        zimfarm_notification=zimfarm_notification,
    )
    session.add(book)
    zimfarm_notification.events.append(
        f"{getnow()}: notification transformed into book"
    )
    book.events.append(
        f"{getnow()}: created from Zimfarm notification {zimfarm_notification.id}"
    )

    return book
