from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, BookLocation, Warehouse, ZimfarmNotification
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

    # Extract metadata fields (optional fields may not be present)
    name = zim_metadata.get("Name")
    date = zim_metadata.get("Date")
    flavour = zim_metadata.get("Flavour")

    book = Book(
        id=book_id,
        created_at=getnow(),
        article_count=article_count,
        media_count=media_count,
        size=size,
        zim_metadata=zim_metadata,
        zimcheck_result=zimcheck_result,
        name=name,
        date=date,
        flavour=flavour,
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


def create_book_location(
    session: OrmSession,
    *,
    book: Book,
    warehouse_id: UUID,
    path: Path,
    filename: str,
    status: str = "current",
) -> BookLocation:
    """Create a new book location.

    Args:
        session: SQLAlchemy session
        book: Book instance
        warehouse_id: ID of the warehouse
        path: Folder path within the warehouse (e.g., "dev-zim")
        filename: Filename in warehouse
        status: Location status ('current' or 'target'), defaults to 'current'

    Returns:
        Created BookLocation instance
    """
    # Get warehouse info for event message
    warehouse = session.get(Warehouse, warehouse_id)
    if not warehouse:
        raise ValueError(f"Warehouse with id {warehouse_id} not found")

    warehouse_name = warehouse.name

    location = BookLocation(
        book_id=book.id,
        warehouse_id=warehouse_id,
        path=path,
        status=status,
        filename=filename,
    )
    session.add(location)
    book.locations.append(location)
    book.events.append(
        f"{getnow()}: added {status} location: {filename} in {warehouse_name}: "
        f"{path} ({warehouse_id})"
    )

    return location


def get_next_book_to_move_files_or_none(
    session: OrmSession,
) -> Book | None:
    return session.scalars(
        select(Book)
        .where(Book.status == "pending_move")
        .order_by(Book.created_at)
        .limit(1)
    ).one_or_none()
