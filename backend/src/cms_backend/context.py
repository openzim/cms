import dataclasses
import os
from pathlib import Path
from typing import Any, TypeVar

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

    base_dir: Path = Path(__file__).parent.parent

    debug: bool = parse_bool(os.getenv("DEBUG", "False"))

    # URL to connect to the database
    database_url: str = get_mandatory_env("DATABASE_URL")
