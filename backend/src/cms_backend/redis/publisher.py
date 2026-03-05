from cms_backend import logger
from cms_backend.context import Context
from cms_backend.redis import get_redis_connection
from cms_backend.utils.datetime import getnow


class RedisPublisher:
    """Publisher for sending events to Mill via Redis Streams."""

    _instance = None
    _redis_client = None

    def __new__(cls):
        """Singleton pattern to reuse Redis connection across requests."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Redis client."""
        if self._redis_client is None:
            self._redis_client = get_redis_connection()
            logger.debug("Acquired redis connection.")

    def publish_title_modified(
        self,
        title_id: str,
        title_name: str,
        action: str,
    ) -> str | None:
        """Publish a title modification event to Redis Stream."""
        if self._redis_client is None:
            raise ValueError("Redis client not connected.")

        try:
            message_id = self._redis_client.xadd(
                Context.mill_events_key,
                {
                    "event_type": "TITLE_MODIFIED",
                    "title_id": title_id,
                    "title_name": title_name,
                    "action": action,
                    "timestamp": getnow().isoformat(),
                },
                maxlen=10000,  # Keep last 10k messages (prevent unbounded growth)
            )
            logger.info(
                f"Published title modification event to Redis: "
                f"{action} '{title_name}' ({title_id}) - message_id: {message_id}"
            )
            return message_id  # pyright: ignore[reportReturnType]
        except Exception as exc:
            logger.exception(f"Failed to publish to Redis Stream: {exc}. ")
            return None

    def close(self):
        """Close Redis connection."""
        if self._redis_client:
            self._redis_client.close()
            logger.debug("Closed redis connection.")
