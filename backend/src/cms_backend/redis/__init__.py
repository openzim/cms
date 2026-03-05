import redis

from cms_backend import logger
from cms_backend.context import Context


def get_redis_connection() -> redis.Redis:
    """Get a connection to Reids."""
    try:
        client = redis.Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            Context.redis_database_url,
            decode_responses=True,
        )
        client.ping()  # pyright: ignore[reportUnknownMemberType]
    except redis.RedisError as exc:
        logger.error(f"Failed to connect to Redis: {exc}")
        raise

    return client
