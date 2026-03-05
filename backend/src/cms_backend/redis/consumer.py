from dataclasses import dataclass
from typing import Any

from cms_backend import logger
from cms_backend.redis import get_redis_connection


@dataclass
class Event:
    """Model of Redis stream events."""

    message_id: str
    data: dict[str, Any]
    stream_name: str


class RedisConsumer:
    """Consumer for receiving events from API via Redis Streams.

    Uses Redis Streams consumer groups for reliable message processing.
    Multiple Mill instances can share work via the same consumer group.
    """

    def __init__(self, *, consumer_name: str, stream_key: str, group_name: str):
        """Initialize Redis consumer."""
        self.consumer_name = consumer_name
        self.stream_key = stream_key
        self.group_name = group_name

        self._redis_client = get_redis_connection()
        self._check_backlog: bool = True
        self._ensure_consumer_group()

    def _ensure_consumer_group(self):
        """Create consumer group if it doesn't exist."""
        try:
            self._redis_client.xgroup_create(
                name=self.stream_key,
                groupname=self.group_name,
                id="0",  # start from the first message in the queue
                mkstream=True,
            )
            logger.info(f"Created consumer group '{self.group_name}'")
        except Exception as exc:
            if "BUSYGROUP" in str(exc):
                logger.debug(f"Consumer group '{self.group_name}' already exists")
            else:
                raise

    def read_events(
        self,
        *,
        block_ms: int = 2000,
        count: int = 10,
    ) -> list[Event]:
        """Read events from Redis Streams.

        First, check for pending messages (messages we read but didn't ACK)
        If no pending, read new messages

        This ensures we never lose messages after a crash or restart.
        """
        try:
            # Check for pending messages (from this consumer)
            if self._check_backlog:
                stream_id = "0"  # '0' means my pending messages
            else:
                stream_id = ">"  # '>' means new messages

            result = self._redis_client.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_key: stream_id},
                count=count,
                block=block_ms,
            )

            if not result:
                logger.debug("Timeout! No new messages.")
                return []

            self._check_backlog = (
                False
                if result
                and len(
                    result[  # pyright: ignore[reportUnknownArgumentType, reportIndexIssue]
                        0
                    ][
                        1
                    ]
                )
                == 0
                else True
            )
            return self._parse_stream_result(result)

        except Exception:
            logger.exception("Error reading from Redis Stream")
            return []

    def _parse_stream_result(self, result: Any) -> list[Event]:
        """Parse Redis XREADGROUP result into event dictionaries."""
        events: list[Event] = []
        # Result format: [('stream_name', [('msg_id', {'field': 'value'}), ...])]
        for stream_name, messages in result:
            for message_id, data in messages:
                events.append(
                    Event(message_id=message_id, data=data, stream_name=stream_name)
                )

        return events

    def acknowledge_event(self, message_id: str):
        """Acknowledge that an event was successfully processed."""
        try:
            self._redis_client.xack(self.stream_key, self.group_name, message_id)
            logger.info(f"Acknowledged message {message_id}")
        except Exception:
            logger.exception(f"Error acknowledging message {message_id}")

    def close(self):
        """Close Redis connection."""
        if self._redis_client:
            self._redis_client.close()
            logger.info("Redis consumer closed")
