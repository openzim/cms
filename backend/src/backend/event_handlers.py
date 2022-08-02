from typing import Optional

from pymitter import EventEmitter

from backend.models import ACTION_ADD, Book, LogEntry, Title

ee = EventEmitter()


@ee.on("added_book")
async def added_book(target: Book, message: Optional[str] = None):
    await LogEntry.add(
        target=target,
        action=ACTION_ADD,
        message=message or f"Added {repr(target)}",
    )


@ee.on("added_book_metadata")
async def added_book_metadata(target: Book, message: Optional[str] = None):
    await LogEntry.add(
        target=target,
        action=ACTION_ADD,
        message=message or f"Added book metadata to {repr(target)}",
    )


@ee.on("added_title_metadata")
async def added_title_metadata(target: Title, message: Optional[str] = None):
    await LogEntry.add(
        target=target,
        action=ACTION_ADD,
        message=message or f"Added title metadata to {repr(target)}",
    )


@ee.on("added_book_tag")
async def added_book_tag(target: Book, message: Optional[str] = None):
    await LogEntry.add(
        target=target,
        action=ACTION_ADD,
        message=message or f"Added book tag to {repr(target)}",
    )
