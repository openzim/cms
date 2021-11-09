import os
from dataclasses import dataclass


@dataclass
class BackendConf:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///dev.db")
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
