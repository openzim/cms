from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from cms_backend.api.routes.fields import NotEmptyString
from cms_backend.schemas import BaseModel

T = TypeVar("T")


class ListResult[T](BaseModel):
    nb_records: int
    records: list[T]


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
    flavours: list[str]


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


class TitleHistorySchema(TitleLightSchema):
    """
    Schema for reading a title history model
    """

    id: UUID
    comment: str | None
    author: str
    collections: list[BaseTitleCollectionSchema]
    created_at: datetime


class CollectionLightSchema(BaseModel):
    """Schema for reading a collection with all the paths in it."""

    id: UUID
    name: str
    paths: list[Path]


class CollectionFullSchema(BaseModel):
    """Schema for reading a collection with all the fileds inlcuding warehouse."""

    id: UUID
    name: str
    warehouse: str
    download_base_url: str | None = None
    view_base_url: str | None = None
    article_count_change_threshold: float | None = None
    media_count_change_threshold: float | None = None


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
    flavour: str | None
    issues: list[str]
    has_flavour_mismatch: bool


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
    article_count_change_threshold: float | None
    media_count_change_threshold: float | None


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
