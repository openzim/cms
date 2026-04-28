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

    process_title_modifications_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("PROCESS_TILTE_MODIFICATIONS_INTERVAL", default="1m")
        )
    )

    process_retention_rules_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("PROCESS_RETENTION_RULES_INTERVAL", default="1d")
        )
    )
