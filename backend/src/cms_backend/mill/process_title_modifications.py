from uuid import UUID

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db import Session
from cms_backend.db.title import get_title_by_id
from cms_backend.mill.context import Context as MillContext
from cms_backend.mill.processors.title_modification import process_title_modification
from cms_backend.redis.consumer import RedisConsumer


def process_title_modifications_from_stream():
    """Process title modification events from Redis stream."""

    consumer = RedisConsumer(
        consumer_name=MillContext.stream_processor_consumer,
        stream_key=Context.mill_events_key,
        group_name="mill-stream-group",
    )
    logger.info("Starting title modification event processor...")

    try:
        while True:
            events = consumer.read_events(block_ms=2000, count=10)

            if not events:
                logger.debug("No title modification events to process")
                continue

            logger.info(f"Processing {len(events)} title modification event(s)")

            with Session.begin() as session:
                for event in events:
                    try:
                        event_type = event.data.get("event_type")
                        if event_type != "TITLE_MODIFIED":
                            logger.warning(
                                f"Unknown event type '{event_type}' in message "
                                f"{event.message_id}, skipping"
                            )
                            consumer.acknowledge_event(event.message_id)
                            continue

                        title_id_str = event.data.get("title_id")
                        title_name = event.data.get("title_name")
                        action = event.data.get("action")

                        if not title_id_str or not title_name:
                            logger.error(
                                f"Missing title_id or title_name in event "
                                f"{event.message_id}, skipping"
                            )
                            consumer.acknowledge_event(event.message_id)
                            continue

                        logger.info(
                            f"Processing TITLE_MODIFIED event: {action} title "
                            f"'{title_name}' (ID: {title_id_str})"
                        )

                        with session.begin_nested():
                            try:
                                title = get_title_by_id(
                                    session, title_id=UUID(title_id_str)
                                )
                                process_title_modification(session, title)
                                consumer.acknowledge_event(event.message_id)

                                logger.info(
                                    f"Successfully processed event {event.message_id} "
                                    f"for title '{title_name}' (ID: {title_id_str})"
                                )

                            except Exception:
                                logger.exception(
                                    f"Error processing event {event.message_id} for "
                                    f"title {title_id_str}"
                                )
                                # Should we acknowledge event?
                                continue

                    except Exception:
                        logger.exception(
                            f"Unexpected error processing event {event.message_id}"
                        )

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down gracefully...")
    except Exception as exc:
        logger.exception(f"Fatal error in title modification processor: {exc}")
        raise
    finally:
        consumer.close()
        logger.info("Title modification event processor stopped")
