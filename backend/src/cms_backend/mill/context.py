import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from humanfriendly import parse_timespan

from cms_backend.context import get_mandatory_env

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

    jail_warehouse_id: UUID = field(
        default=UUID(get_mandatory_env("JAIL_WAREHOUSE_ID"))
    )
    jail_base_path: Path = field(default=Path(os.getenv("JAIL_BASE_PATH", "")))

    staging_warehouse_id: UUID = field(
        default=UUID(get_mandatory_env("STAGING_WAREHOUSE_ID"))
    )
    staging_base_path: Path = field(default=Path(os.getenv("STAGING_BASE_PATH", "")))
