from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from pydantic import Field, computed_field

from cms_backend import (
    construct_recipe_api_link,
    construct_recipe_link,
    construct_task_api_link,
    construct_task_link,
)
from cms_backend.context import Context
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import NotEmptyString
from cms_backend.utils.datetime import getnow

T = TypeVar("T")


class ListResult[T](BaseModel):
    nb_records: int
    records: list[T]


class BaseTitleFlavourSchema(BaseModel):
    flavour: str
    recipe_id: UUID | None


class TitleFlavourSchema(BaseTitleFlavourSchema):
    last_book_added_at: datetime | None

    @computed_field
    @property
    def recipe_link(self) -> str | None:
        return construct_recipe_link(self.recipe_id)

    @computed_field
    @property
    def recipe_api_link(self) -> str | None:
        return construct_recipe_api_link(self.recipe_id)

    @computed_field
    @property
    def is_rotten(self) -> bool:
        if self.last_book_added_at is None:
            return False
        return self.last_book_added_at < (getnow() - Context.rotten_flavour_threshold)


class TitleLightSchema(BaseModel):
    """
    Schema for reading a title model with some fields
    """

    id: UUID
    name: str
    maturity: str | None
    archived: bool
    title: str | None
    creator: str | None
    publisher: str | None
    description: str | None
    language: str | None
    illustration_48x48_at_1: str | None
    long_description: str | None
    license: str | None
    relation: str | None
    source: str | None


class BaseTitleCollectionSchema(BaseModel):
    collection_name: NotEmptyString
    path: str


class TitleCollectionSchema(BaseTitleCollectionSchema):
    collection_id: UUID


class TitleFullSchema(TitleLightSchema):
    """
    Schema for reading a title model with all fields including books
    """

    events: list[str]
    books: list["BookLightSchema"]
    collections: list["TitleCollectionSchema"]
    flavours: list[TitleFlavourSchema]


class TitleHistorySchema(TitleLightSchema):
    """
    Schema for reading a title history model
    """

    id: UUID
    comment: str | None
    author: str
    collections: list[BaseTitleCollectionSchema]
    created_at: datetime
    flavours: list[BaseTitleFlavourSchema]


class CollectionLightSchema(BaseModel):
    """Schema for reading a collection with all the paths in it."""

    id: UUID
    name: str
    paths: list[Path]
    is_private: bool


class CollectionFullSchema(BaseModel):
    """Schema for reading a collection with all the fileds inlcuding warehouse."""

    id: UUID
    name: str
    warehouse: str
    is_private: bool
    download_base_url: str | None = None
    view_base_url: str | None = None
    article_count_increase_threshold: float | None = None
    media_count_increase_threshold: float | None = None
    article_count_decrease_threshold: float | None = None
    media_count_decrease_threshold: float | None = None


class ZimfarmNotificationLightSchema(BaseModel):
    """
    Schema for reading a zimfarm notification model with some fields
    """

    id: UUID
    book_id: UUID | None
    status: str
    received_at: datetime


class ZimfarmNotificationFullSchema(ZimfarmNotificationLightSchema):
    content: dict[str, Any]
    events: list[str]


class BookLocationSchema(BaseModel):
    """
    Schema for book location information
    """

    warehouse_name: str
    path: str
    filename: str
    status: str  # 'current' or 'target'
    is_backup: bool


class BookLightSchema(BaseModel):
    """
    Schema for reading a book model with some fields
    """

    id: UUID
    title_id: UUID | None
    title_name: str | None
    location_kind: str  # 'quarantine', 'staging', or 'prod'
    needs_processing: bool
    has_error: bool
    needs_file_operation: bool
    deletion_date: datetime | None
    created_at: datetime
    name: str | None
    date: str | None
    flavour: str
    issues: list[str]
    offliner: str | None


class ZimcheckSummarySchema(BaseModel):
    zimcheck_version: str | None = None
    status: bool | None = None
    checks: list[str] | None = None
    error_count: int | None = None
    warning_count: int | None = None
    retcode: int | None = None


class BookFullSchema(BookLightSchema):
    article_count: int
    media_count: int
    size: int
    zimcheck_result_url: str | None
    zim_metadata: dict[str, Any]
    events: list[str]
    current_locations: list[BookLocationSchema]
    target_locations: list[BookLocationSchema]
    title_archived: bool
    has_backup: bool
    zimcheck_summary: ZimcheckSummarySchema | None
    zimcheck_s3_deleted: bool
    recipe_id: UUID | None
    task_id: UUID | None = Field(exclude=None)

    @computed_field
    @property
    def recipe_link(self) -> str | None:
        return construct_recipe_link(self.recipe_id)

    @computed_field
    @property
    def recipe_api_link(self) -> str | None:
        return construct_recipe_api_link(self.recipe_id)

    @computed_field
    @property
    def task_link(self) -> str | None:
        return construct_task_link(self.task_id)

    @computed_field
    @property
    def task_api_link(self) -> str | None:
        return construct_task_api_link(self.task_id)


class BookHistorySchema(BaseModel):
    """
    Schema for reading a book history model
    """

    id: UUID
    comment: str | None
    author: str
    name: str | None
    flavour: str | None
    created_at: datetime


class CollectionHistorySchema(BaseModel):
    """
    Schema for reading a collection history model
    """

    id: UUID
    comment: str | None
    author: str
    name: str | None
    created_at: datetime
    download_base_url: str | None
    view_base_url: str | None
    is_private: bool
    article_count_increase_threshold: float | None = None
    media_count_increase_threshold: float | None = None
    article_count_decrease_threshold: float | None = None
    media_count_decrease_threshold: float | None = None


class WarehousePathSchema(BaseModel):
    """
    Schema for reading warehouse path with warehouse information
    """

    path_id: UUID
    folder_name: str
    warehouse_id: UUID
    warehouse_name: str


class AccountSchema(BaseModel):
    """
    Schema for reading an account model
    """

    id: UUID
    username: str | None
    display_name: str
    role: str
    scope: dict[str, dict[str, bool]]
    idp_sub: UUID | None
    has_password: bool


class EventLightSchema(BaseModel):
    """
    Schema for reading an event model.
    """

    id: UUID
    created_at: datetime
    topic: str


class RequestedTaskLightSchema(BaseModel):
    id: UUID
    status: str
    requested_by: str | None
    created_at: datetime
    s3_url: str = Field(exclude=True)
    s3_key: str = Field(exclude=True)
    recipe_id: UUID = Field(exclude=True)
