import os
from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar, TypeVar

from humanfriendly import parse_timespan

from cms_backend.context import parse_bool

T = TypeVar("T")


def _parse_internal_host_mapping(value: str) -> dict[str, str]:
    """Parse the INTERNAL_HOST_MAPPING env var into a public->internal host dict.

    Expected format: "public.host:internal.host,other.host:other.internal".
    """
    mapping: dict[str, str] = {}
    for entry in value.split(","):
        public_host, separator, internal_host = entry.strip().partition(":")
        if separator and public_host.strip() and internal_host.strip():
            mapping[public_host.strip()] = internal_host.strip()
    return mapping


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

    process_zimfarm_notifications_enabled: bool = parse_bool(
        os.getenv("PROCESS_ZIMFARM_NOTIFICATIONS", default="true")
    )

    process_events_interval: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("PROCESS_EVENTS_INTERVAL", default="1m"))
    )

    process_title_modifications_enabled: bool = parse_bool(
        os.getenv("PROCESS_TITLE_MODIFICATIONS", default="true")
    )

    process_app_build_requests_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("PROCESS_APP_BUILD_REQUESTS_INTERVAL", default="10s")
        )
    )

    process_app_build_requests_enabled: bool = parse_bool(
        os.getenv("PROCESS_APP_BUILD_REQUESTS", default="true")
    )

    advance_app_builds_interval: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("ADVANCE_APP_BUILDS_INTERVAL", default="30s"))
    )

    advance_app_builds_enabled: bool = parse_bool(
        os.getenv("ADVANCE_APP_BUILDS", default="true")
    )

    check_book_transitions_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("CHECK_BOOK_TRANSITIONS_INTERVAL", default="1m")
        )
    )

    check_book_transitions_enabled: bool = parse_bool(
        os.getenv("CHECK_BOOK_TRANSITIONS", default="true")
    )

    process_retention_rules_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("PROCESS_RETENTION_RULES_INTERVAL", default="1d")
        )
    )

    process_retention_rules_enabled: bool = parse_bool(
        os.getenv("PROCESS_RETENTION_RULES", default="true")
    )

    mark_staging_books_for_deletion_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("MARK_STAGING_BOOKS_FOR_DELETION_INTERVAL", default="1d")
        )
    )

    mark_staging_books_for_deletion_enabled: bool = parse_bool(
        os.getenv("MARK_STAGING_BOOKS_FOR_DELETION", default="true")
    )

    staging_books_lifespan: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("STAGING_BOOKS_LIFESPAN", default="30d"))
    )

    staging_books_deletion_grace_period: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("STAGING_BOOKS_DELETION_GRACE_PERIOD", default="7d")
        )
    )

    update_title_upload_status_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("UPDATE_TITLE_UPLOAD_STATUS_INTERVAL", default="1m")
        )
    )

    update_title_uploads_status_enabled: bool = parse_bool(
        os.getenv("UPDATE_TITLE_UPLOADS_STATUS", default="true")
    )

    delete_uploaded_zims_interval: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("DELETE_UPLOADED_ZIMS_INTERVAL", default="1d"))
    )

    delete_uploaded_zims_enabled: bool = parse_bool(
        os.getenv("DELETE_UPLOADED_ZIMS", default="true")
    )

    zimcheck_results_s3_bucket_uri: str = os.getenv(
        "ZIMCHECK_RESULTS_S3_BUCKET_URI", default=""
    )
    delete_zimcheck_files_interval: timedelta = timedelta(
        seconds=parse_timespan(
            os.getenv("DELETE_ZIMCHECK_FILES_INTERVAL", default="1h")
        )
    )

    delete_zimcheck_s3_results_enabled: bool = parse_bool(
        os.getenv("DELETE_ZIMCHECK_S3_RESULTS", default="true")
    )

    fetch_download_stats_interval: timedelta = timedelta(
        seconds=parse_timespan(os.getenv("FETCH_DOWNLOAD_STATS_INTERVAL", default="1d"))
    )

    fetch_download_stats_enabled: bool = parse_bool(
        os.getenv("FETCH_DOWNLOAD_STATS", default="true")
    )

    # Delay (in seconds) between two Matomo API requests, to avoid hammering it
    download_stats_request_delay: float = float(
        os.getenv("DOWNLOAD_STATS_REQUEST_DELAY", "10")
    )

    # Map public-facing hostnames to internal service hostnames.
    internal_host_mapping: ClassVar[dict[str, str]] = _parse_internal_host_mapping(
        os.getenv("INTERNAL_HOST_MAPPING", "")
    )
