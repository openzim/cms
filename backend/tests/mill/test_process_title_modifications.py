from collections.abc import Callable
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Book, Title
from cms_backend.mill.process_title_modifications import (
    process_title_modifications_from_stream,
)
from cms_backend.redis.consumer import Event


@patch("cms_backend.mill.process_title_modifications.Session")
@patch("cms_backend.mill.process_title_modifications.RedisConsumer")
def test_process_title_modifications_single_event(
    mock_consumer_class: MagicMock,
    mock_session_class: MagicMock,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    mock_redis_consumer: MagicMock,
):
    """Test processing a single title modification event."""
    mock_consumer_class.return_value = mock_redis_consumer

    @contextmanager
    def mock_session_begin():
        yield dbsession

    mock_session_class.begin = mock_session_begin

    # Create a title and a book without title
    title = create_title(name="wikipedia_en_all")
    book = create_book(
        name="wikipedia_en_all",
        date="2025-01",
        zim_metadata={
            "Name": "wikipedia_en_all",
            "Title": "Wikipedia",
            "Creator": "Wikipedia Contributors",
            "Publisher": "Kiwix",
            "Date": "2025-01",
            "Description": "Wikipedia Encyclopedia",
            "Language": "eng",
        },
    )
    book.title_id = None
    dbsession.flush()

    event = Event(
        message_id="1234-0",
        data={
            "event_type": "TITLE_MODIFIED",
            "title_id": str(title.id),
            "title_name": "wikipedia_en_all",
            "action": "created",
            "timestamp": "2025-01-15T10:00:00",
        },
        stream_name="mill:events",
    )

    # Set up mock to return one event, then raise KeyboardInterrupt
    mock_redis_consumer.read_events.side_effect = [[event], KeyboardInterrupt()]
    process_title_modifications_from_stream()
    mock_redis_consumer.acknowledge_event.assert_called_once_with("1234-0")
    mock_redis_consumer.close.assert_called_once()

    dbsession.refresh(book)
    assert book.title_id == title.id


@patch("cms_backend.mill.process_title_modifications.Session")
@patch("cms_backend.mill.process_title_modifications.RedisConsumer")
def test_process_title_modifications_multiple_events(
    mock_consumer_class: MagicMock,
    mock_session_class: MagicMock,
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
    mock_redis_consumer: MagicMock,
):
    """Test processing multiple title modification events in one batch."""
    mock_consumer_class.return_value = mock_redis_consumer

    @contextmanager
    def mock_session_begin():
        yield dbsession

    mock_session_class.begin = mock_session_begin

    title1 = create_title(name="wikipedia_en_all")
    title2 = create_title(name="wikivoyage_fr_all")

    book1 = create_book(
        name="wikipedia_en_all",
        date="2025-01",
        zim_metadata={
            "Name": "wikipedia_en_all",
            "Title": "Wikipedia",
            "Creator": "Wikipedia Contributors",
            "Publisher": "Kiwix",
            "Date": "2025-01",
            "Description": "Wikipedia Encyclopedia",
            "Language": "eng",
        },
    )
    book1.title_id = None

    book2 = create_book(
        name="wikivoyage_fr_all",
        date="2025-01",
        zim_metadata={
            "Name": "wikivoyage_fr_all",
            "Title": "Wikivoyage",
            "Creator": "Wikivoyage Contributors",
            "Publisher": "Kiwix",
            "Date": "2025-01",
            "Description": "Wikivoyage Travel Guide",
            "Language": "fra",
        },
    )
    book2.title_id = None

    dbsession.flush()

    event1 = Event(
        message_id="1234-0",
        data={
            "event_type": "TITLE_MODIFIED",
            "title_id": str(title1.id),
            "title_name": "wikipedia_en_all",
            "action": "created",
            "timestamp": "2025-01-15T10:00:00",
        },
        stream_name="mill:events",
    )

    event2 = Event(
        message_id="1234-1",
        data={
            "event_type": "TITLE_MODIFIED",
            "title_id": str(title2.id),
            "title_name": "wikivoyage_fr_all",
            "action": "created",
            "timestamp": "2025-01-15T10:01:00",
        },
        stream_name="mill:events",
    )

    mock_redis_consumer.read_events.side_effect = [
        [event1, event2],
        KeyboardInterrupt(),
    ]

    process_title_modifications_from_stream()

    assert mock_redis_consumer.acknowledge_event.call_count == 2
    mock_redis_consumer.acknowledge_event.assert_any_call("1234-0")
    mock_redis_consumer.acknowledge_event.assert_any_call("1234-1")

    dbsession.refresh(book1)
    dbsession.refresh(book2)
    assert book1.title_id == title1.id
    assert book2.title_id == title2.id


@patch("cms_backend.mill.process_title_modifications.Session")
@patch("cms_backend.mill.process_title_modifications.RedisConsumer")
def test_process_title_modifications_unknown_event_type(
    mock_consumer_class: MagicMock,
    mock_session_class: MagicMock,
    dbsession: OrmSession,
    mock_redis_consumer: MagicMock,
):
    """Test that unknown event types are skipped and acknowledged."""
    mock_consumer_class.return_value = mock_redis_consumer

    @contextmanager
    def mock_session_begin():
        yield dbsession

    mock_session_class.begin = mock_session_begin

    event = Event(
        message_id="1234-0",
        data={
            "event_type": "UNKNOWN_EVENT",
            "some_data": "value",
        },
        stream_name="mill:events",
    )
    mock_redis_consumer.read_events.side_effect = [[event], KeyboardInterrupt()]
    process_title_modifications_from_stream()
    mock_redis_consumer.acknowledge_event.assert_called_once_with("1234-0")


@patch("cms_backend.mill.process_title_modifications.Session")
@patch("cms_backend.mill.process_title_modifications.RedisConsumer")
def test_process_title_modifications_missing_title_id(
    mock_consumer_class: MagicMock,
    mock_session_class: MagicMock,
    dbsession: OrmSession,
    mock_redis_consumer: MagicMock,
):
    """Test that events missing title_id are skipped and acknowledged."""
    mock_consumer_class.return_value = mock_redis_consumer

    @contextmanager
    def mock_session_begin():
        yield dbsession

    mock_session_class.begin = mock_session_begin

    event = Event(
        message_id="1234-0",
        data={
            "event_type": "TITLE_MODIFIED",
            "title_name": "wikipedia_en_all",
            "action": "created",
        },
        stream_name="mill:events",
    )

    mock_redis_consumer.read_events.side_effect = [[event], KeyboardInterrupt()]
    process_title_modifications_from_stream()
    mock_redis_consumer.acknowledge_event.assert_called_once_with("1234-0")


@patch("cms_backend.mill.process_title_modifications.Session")
@patch("cms_backend.mill.process_title_modifications.RedisConsumer")
def test_process_title_modifications_missing_title_name(
    mock_consumer_class: MagicMock,
    mock_session_class: MagicMock,
    dbsession: OrmSession,
    mock_redis_consumer: MagicMock,
):
    """Test that events missing title_name are skipped and acknowledged."""
    mock_consumer_class.return_value = mock_redis_consumer

    @contextmanager
    def mock_session_begin():
        yield dbsession

    mock_session_class.begin = mock_session_begin

    event = Event(
        message_id="1234-0",
        data={
            "event_type": "TITLE_MODIFIED",
            "title_id": str(UUID("12345678-1234-5678-1234-567812345678")),
            "action": "created",
        },
        stream_name="mill:events",
    )

    mock_redis_consumer.read_events.side_effect = [[event], KeyboardInterrupt()]
    process_title_modifications_from_stream()
    mock_redis_consumer.acknowledge_event.assert_called_once_with("1234-0")
