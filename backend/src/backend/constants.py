import os
from dataclasses import dataclass


@dataclass
class BackendConf:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///dev.db")
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
