from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import AnyUrl

from cms_backend.api.routes.fields import NotEmptyString
from cms_backend.roles import RoleEnum
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


class AccountUpdateSchema(BaseModel):
    """
    Schema for updating an account
    """

    role: RoleEnum | None = None
    username: NotEmptyString | None = None
    idp_sub: NotEmptyString | None = None
    display_name: NotEmptyString | None = None
