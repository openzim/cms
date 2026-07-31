import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import ClassVar
from uuid import UUID

from humanfriendly import parse_timespan

WarehouseId = str
LocalWarehousePath = str


def _parse_local_warehouse_paths() -> dict[UUID, Path]:
    env_value = os.getenv("LOCAL_WAREHOUSE_PATHS", default="")
    if not env_value:
        return {}
    return {
        UUID(warehouse_id): Path(local_path)
        for item in env_value.split(",")
        if item
        for (warehouse_id, local_path) in [item.split(":", 1)]
    }


@dataclass(kw_only=True)
class Context:
    """Class holding every contextual / configuration bits which can be moved

    Used to easily pass information around in the backend. One singleton instance is
    always available.
    """

    pause_in_the_loop: float = parse_timespan(
        os.getenv("PAUSE_IN_THE_LOOP", default="10s")
    )

    move_files_interval: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("MOVE_FILES_INTERVAL", default="1m"))
    )

    delete_files_interval: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("DELETE_FILES_INTERVAL", default="1h"))
    )

    local_warehouse_paths: ClassVar[dict[UUID, Path]] = _parse_local_warehouse_paths()
