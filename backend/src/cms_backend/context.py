import dataclasses
import os
import re
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


def _validate_regex(regex: str | None) -> re.Pattern[str] | None:
    if regex is None:
        return None
    return re.compile(regex)


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
    # OPDS catalogs: whether the book illustration is embedded as a base64
    # "data:" URL (True) or referenced through opds_illustration_url_template
    # (False).
    opds_inline_illustration: bool = field(
        default=parse_bool(os.getenv("OPDS_INLINE_ILLUSTRATION", "True"))
    )
    # Template used to build the illustration URL when opds_inline_illustration
    # is False. The only placeholder supported is {book_id} which is replaced
    # with the book UUID. Example:
    # https://api.cms.openzim.org/v1/books/{book_id}/raw_metadata/Illustration_48x48%401
    opds_illustration_url_template: str | None = field(
        default=os.getenv("OPDS_ILLUSTRATION_URL_TEMPLATE") or None
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
    media_count_increase_threshold: float = field(
        default=float(os.getenv("MEDIA_COUNT_INCREASE_THRESHOLD", "0.2"))
    )
    article_count_increase_threshold: float = field(
        default=float(os.getenv("ARTICLE_COUNT_INCREASE_THRESHOLD", "0.2"))
    )
    media_count_decrease_threshold: float = field(
        default=float(os.getenv("MEDIA_COUNT_DECREASE_THRESHOLD", "0.1"))
    )
    article_count_decrease_threshold: float = field(
        default=float(os.getenv("ARTICLE_COUNT_DECREASE_THRESHOLD", "0.1"))
    )
    zim_title_max_length: int = field(
        default=int(os.getenv("ZIM_TITLE_MAX_LENGTH", "30"))
    )
    zim_description_max_length: int = field(
        default=int(os.getenv("ZIM_DESCRIPTION_MAX_LENGTH", "80"))
    )
    requests_timeout: int = field(
        default=int(parse_timespan(os.getenv("REQUESTS_TIMEOUT", default="30s")))
    )
    # Regex of scrapers to ignore when running checks for zimcheck quality
    # e.g mwoflliner*|sotoki*
    zimcheck_scrapers_whitelist_regex: ClassVar[re.Pattern[str] | None] = (
        _validate_regex(os.getenv("ZIMCHECK_SCRAPERS_WHITELIST_REGEX"))
    )

    zimfarm_url: str = field(
        default=os.getenv("ZIMFARM_URL", "https://farm.openzim.org")
    )

    zimfarm_api_url: str = field(
        default=os.getenv("ZIMFARM_API_URL", "https://api.farm.openzim.org/v2")
    )

    rotten_flavour_threshold: timedelta = field(
        default=timedelta(
            seconds=parse_timespan(os.getenv("ROTTEN_FLAVOUR_THRESHOLD", default="56w"))
        )
    )
    zim_upload_s3_bucket_uri: str = os.getenv("ZIM_UPLOAD_S3_BUCKET_URI", default="")

    # Matomo instance used to collect download statistics
    matomo_url: str = field(default=os.getenv("MATOMO_URL", "https://stats.kiwix.org/"))
    # Matomo site id of the download server (lb.download.kiwix.org)
    matomo_site_id: int = field(default=int(os.getenv("MATOMO_SITE_ID", "24")))
    # How far back (in days) download statistics must be fetched
    download_stats_days_ago: int = field(
        default=int(os.getenv("DOWNLOAD_STATS_DAYS_AGO", "365"))
    )
    # Hour (UTC) after which the previous day statistics are available
    download_stats_yesterday_hour: int = field(
        default=int(os.getenv("DOWNLOAD_STATS_YESTERDAY_HOUR", "4"))
    )
    # Number of most recent days of download stats used to compute popularity
    download_stats_popularity_window_days: int = field(
        default=int(os.getenv("DOWNLOAD_STATS_POPULARITY_WINDOW_DAYS", "7"))
    )
