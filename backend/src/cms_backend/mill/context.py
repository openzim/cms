import os
from dataclasses import dataclass
from datetime import timedelta
from typing import TypeVar

from humanfriendly import parse_timespan

T = TypeVar("T")


@dataclass(kw_only=True)
class Context:
    """Class holding every contextual / configuration bits which can be moved

    Used to easily pass information around in the backend. One singleton instance is
    always available.
    """

    pause_in_the_loop: float = parse_timespan(
        os.getenv("PAUSE_IN_THE_LOOP", default="10s")
    )

    process_zimfarm_notifications_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("PROCESS_ZIMFARM_NOTIFICATIONS_INTERVAL", default="1m")
        )
    )

    process_events_interval: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("PROCESS_EVENTS_INTERVAL", default="1m"))
    )

    process_retention_rules_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("PROCESS_RETENTION_RULES_INTERVAL", default="1d")
        )
    )

    mark_staging_books_for_deletion_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("MARK_STAGING_BOOKS_FOR_DELETION_INTERVAL", default="1d")
        )
    )

    staging_books_lifespan: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("STAGING_BOOKS_LIFESPAN", default="30d"))
    )

    staging_books_deletion_grace_period: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("STAGING_BOOKS_DELETION_GRACE_PERIOD", default="7d")
        )
    )
