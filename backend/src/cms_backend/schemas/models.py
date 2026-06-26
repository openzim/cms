import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AfterValidator, AnyUrl, Field, model_validator

from cms_backend.api.routes.fields import (
    Base64Str,
    GraphemeLength,
    LangCode,
    NotEmptyString,
    ZimFlavour,
)
from cms_backend.context import Context
from cms_backend.roles import RoleEnum
from cms_backend.schemas import BaseModel
from cms_backend.schemas.orms import BaseTitleCollectionSchema

ZIM_TITLE_NAME_REGEX = re.compile(
    r"^[a-z0-9\-\.]+?_[a-z]{2}(?:-[a-z]{2,10})?_[a-z0-9\-\.]+?$"
)


class ZimUrlSchema(BaseModel):
    """Schema for a single zim URL"""

    kind: Literal["view", "download", "zimcheck"]
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
    is_backup: bool = False


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
    article_count_change_threshold: float | None = Field(ge=0.0, le=1.0, default=None)
    media_count_change_threshold: float | None = Field(ge=0.0, le=1.0, default=None)


class BaseTitleCreateUpdateSchema(BaseModel):
    collection_titles: list[BaseTitleCollectionSchema] | None = None
    long_description: NotEmptyString | None = None
    license: NotEmptyString | None = None
    relation: NotEmptyString | None = None
    source: NotEmptyString | None = None
    title: (
        Annotated[
            NotEmptyString,
            AfterValidator(GraphemeLength(max=Context.zim_title_max_length)),
        ]
        | None
    ) = None
    creator: NotEmptyString | None = None
    description: (
        Annotated[
            NotEmptyString,
            AfterValidator(GraphemeLength(max=Context.zim_description_max_length)),
        ]
        | None
    ) = None
    publisher: NotEmptyString | None = None
    language: LangCode | None = None
    illustration_48x48_at_1: Base64Str | None = None
    flavours: list[ZimFlavour] | None = None
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
    name: NotEmptyString = Field(pattern=ZIM_TITLE_NAME_REGEX)
    maturity: Literal["unstable", "stable"] = "unstable"


class TitleUpdateSchema(BaseTitleCreateUpdateSchema):
    name: NotEmptyString | None = Field(pattern=ZIM_TITLE_NAME_REGEX, default=None)
    maturity: Literal["unstable", "stable"] | None = None
    comment: NotEmptyString | None = None


class BookUpdateSchema(BaseModel):
    comment: NotEmptyString | None = None
    flavour: NotEmptyString | None = None
