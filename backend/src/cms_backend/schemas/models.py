from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import AnyUrl

from cms_backend.schemas import BaseModel


class ZimUrlSchema(BaseModel):
    """Schema for a single zim URL"""

    kind: Literal["view", "download"]
    url: AnyUrl
    collection: str


class ZimUrlsSchema(BaseModel):
    urls: dict[UUID, list[ZimUrlSchema]]


class BookLanguagesSchema(BaseModel):
    languages: list[str]


@dataclass(eq=True, frozen=True)
class FileLocation:
    warehouse_id: UUID
    path: Path
    filename: str
