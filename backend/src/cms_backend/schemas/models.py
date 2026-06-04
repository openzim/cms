from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

from pydantic import AnyUrl, model_validator

from cms_backend.api.routes.fields import Base64Str, NotEmptyString
from cms_backend.roles import RoleEnum
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import BaseTitleCollectionSchema


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


class CollectionUpdateSchema(BaseModel):
    name: NotEmptyString | None = None
    download_base_url: AnyUrl | None = None
    view_base_url: AnyUrl | None = None
    comment: NotEmptyString | None = None


class BaseTitleCreateUpdateSchema(BaseModel):
    collection_titles: list[BaseTitleCollectionSchema] | None = None
    long_description: NotEmptyString | None = None
    license: NotEmptyString | None = None
    relation: NotEmptyString | None = None
    source: NotEmptyString | None = None
    title: NotEmptyString | None = None
    creator: NotEmptyString | None = None
    description: NotEmptyString | None = None
    publisher: NotEmptyString | None = None
    language: NotEmptyString | None = None
    illustration_48x48_at_1: Base64Str | None = None
    flavours: list[str] | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def validate_unique_collection_titles(self) -> Self:
        if self.collection_titles:
            seen: set[str] = set()
            for entry in self.collection_titles:
                if entry.collection_name in seen:
                    raise ValueError(
                        f"Collection title {entry.collection_name} duplicated, "
                        "cannot use a collection twice in a given title"
                    )
                else:
                    seen.add(entry.collection_name)
        return self


class TitleCreateSchema(BaseTitleCreateUpdateSchema):
    name: NotEmptyString
    maturity: Literal["unstable", "stable"] = "unstable"


class TitleUpdateSchema(BaseTitleCreateUpdateSchema):
    name: NotEmptyString | None = None
    maturity: Literal["unstable", "stable"] | None = None
    comment: NotEmptyString | None = None


class BookUpdateSchema(BaseModel):
    comment: NotEmptyString | None = None
    flavour: NotEmptyString | None = None
