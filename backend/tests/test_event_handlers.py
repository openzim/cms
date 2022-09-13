import pytest

from backend.event_handlers import ee
from backend.models import LogEntry


@pytest.mark.asyncio
async def test_emit_add_book(book):
    object_type = str(type(book))
    count_log_entry = await LogEntry.objects.filter(object_type=object_type).count()
    message = f"Added {repr(book)} for test"
    await ee.emit_async("added_book", book, message)
    log_entry = LogEntry.objects.filter(object_type=object_type)
    assert await log_entry.count() == count_log_entry + 1
    assert await LogEntry.objects.get(object_type=object_type, message=message)
    await log_entry.delete()

    await ee.emit_async("added_book", book)
    assert await LogEntry.objects.get(
        object_type=object_type, message=f"Added {repr(book)}"
    )
