import dataclasses
import os
from dataclasses import field
from datetime import timedelta
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from humanfriendly import parse_timespan

T = TypeVar("T")


def parse_bool(value: Any) -> bool:
    """Parse value into boolean."""
    return str(value).lower() in ("true", "1", "yes", "y", "on")


def get_mandatory_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise Exception(f"{key} environment variable must be set")
    return value


@dataclasses.dataclass(kw_only=True)
class Context:
    """Class holding every contextual / configuration bits which can be moved

    Used to easily pass information around in the backend. One singleton instance is
    always available.
    """

    base_dir: Path = Path(__file__).parent

    debug: bool = parse_bool(os.getenv("DEBUG", "False"))

    # URL to connect to the database
    database_url: str = get_mandatory_env("DATABASE_URL")

    # should we run alembic migrations on startup
    alembic_upgrade_head_on_start: bool = parse_bool(
        get_mandatory_env("ALEMBIC_UPGRADE_HEAD_ON_START")
    )

    # delay before books are deleted
    book_deletion_delay: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("BOOK_DELETION_DELAY", default="1d"))
    )
    staging_warehouse_id: UUID = field(
        default=UUID(get_mandatory_env("STAGING_WAREHOUSE_ID"))
    )
    staging_base_path: Path = field(default=Path(os.getenv("STAGING_BASE_PATH", "")))
    quarantine_warehouse_id: UUID = field(
        default=UUID(get_mandatory_env("QUARANTINE_WAREHOUSE_ID"))
    )
    quarantine_base_path: Path = field(
        default=Path(os.getenv("QUARANTINE_BASE_PATH", ""))
    )
