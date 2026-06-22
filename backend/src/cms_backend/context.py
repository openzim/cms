import dataclasses
import os
from dataclasses import field
from datetime import timedelta
from pathlib import Path
from typing import Any, ClassVar, TypeVar
from uuid import UUID

import pycountry
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


def _parse_custom_language_codes(language_code: str | None) -> list[str]:
    """Transform the env language codes (comma-seperated) into a list."""
    if language_code is None:
        return []

    codes = language_code.split(",")
    for code in codes:
        if len(code) != 3:  # noqa: PLR2004
            raise ValueError(f"Custom code '{code}' must be 3 characters long.")
    return codes


def _validate_language_codes(language_codes: list[str]) -> list[str]:
    for code in language_codes:
        if pycountry.languages.get(alpha_3=code) is None:  # pyright: ignore[reportUnknownMemberType]
            raise ValueError(f"Code '{code}' is not a valid ISO 639-3 code.")
    return language_codes


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
    staging_download_base_url: str = field(
        default=get_mandatory_env("STAGING_DOWNLOAD_BASE_URL")
    )
    staging_view_base_url: str = field(
        default=get_mandatory_env("STAGING_VIEW_BASE_URL")
    )
    staging_library_xml_base_path: str = field(
        default=os.getenv("STAGING_LIBRARY_XML_BASE_PATH", "/data/dev/")
    )
    quarantine_warehouse_id: UUID = field(
        default=UUID(get_mandatory_env("QUARANTINE_WAREHOUSE_ID"))
    )
    quarantine_base_path: Path = field(
        default=Path(os.getenv("QUARANTINE_BASE_PATH", ""))
    )
    # Comma-seperated list of custom iso639-3 language codes
    custom_language_codes: ClassVar[list[str]] = _parse_custom_language_codes(
        os.getenv("CUSTOM_LANGUAGE_CODES")
    )
    disallowed_language_codes: ClassVar[list[str]] = _validate_language_codes(
        _parse_custom_language_codes(os.getenv("DISALLOWED_LANGUAGE_CODES"))
    )
    backup_warehouse_id: UUID = field(
        default=UUID(get_mandatory_env("BACKUP_WAREHOUSE_ID"))
    )
    backup_base_path: Path = field(default=Path(os.getenv("BACKUP_BASE_PATH", "")))
    backup_download_base_url: str = field(
        default=os.getenv("BACKUP_DOWNLOAD_BASE_URL", "")
    )
    backup_view_base_url: str = field(default=os.getenv("BACKUP_VIEW_BASE_URL", ""))
    media_count_change_threshold: float = field(
        default=float(os.getenv("MEDIA_COUNT_CHANGE_THRESHOLD", "0.1"))
    )
    article_count_change_threshold: float = field(
        default=float(os.getenv("ARTICLE_COUNT_CHANGE_THRESHOLD", "0.1"))
    )
    zim_title_max_length: int = field(
        default=int(os.getenv("ZIM_TITLE_MAX_LENGTH", "30"))
    )
    zim_description_max_length: int = field(
        default=int(os.getenv("ZIM_DESCRIPTION_MAX_LENGTH", "80"))
    )
