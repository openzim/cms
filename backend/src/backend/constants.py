import logging
import os
import pathlib
from dataclasses import dataclass

from zimscraperlib.logging import getLogger as lib_getLogger

src_dir = pathlib.Path(__file__).parent.resolve()

logger = lib_getLogger(
    src_dir.name,
    level=logging.INFO,
    log_format="[%(asctime)s] %(levelname)s:%(message)s",
)


@dataclass
class BackendConf:
    nb_book_versions_to_keep = os.getenv("NB_BOOK_VERSIONS_TO_KEEP", 2)
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:////{src_dir}/dev.db")
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost|http://localhost:8000|http://localhost:8080",  # dev fallback
    ).split("|")
    mandatory_metadata = (
        "Name",
        "Title",
        "Creator",
        "Publisher",
        "Description",
        "Language",
        "Tags",
        "Date",
        "Counter",
    )
