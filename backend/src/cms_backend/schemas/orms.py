from datetime import datetime
from pathlib import Path
from typing import Any, Generic, TypeVar
from uuid import UUID

from cms_backend.api.routes.fields import NotEmptyString
from cms_backend.schemas import BaseModel

T = TypeVar("T")


class ListResult(BaseModel, Generic[T]):
    nb_records: int
    records: list[T]


class TitleLightSchema(BaseModel):
    """
    Schema for reading a title model with some fields
    """

    id: UUID
    name: str
    maturity: str | None


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


class CollectionLightSchema(BaseModel):
    """Collection for reading a collection with all the paths in it."""

    id: UUID
    name: str
    paths: list[Path]


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


class BookLightSchema(BaseModel):
    """
    Schema for reading a book model with some fields
    """

    id: UUID
    title_id: UUID | None
    location_kind: str  # 'quarantine', 'staging', or 'prod'
    needs_processing: bool
    has_error: bool
    needs_file_operation: bool
    created_at: datetime
    name: str | None
    date: str | None
    flavour: str | None


class BookFullSchema(BookLightSchema):
    article_count: int
    media_count: int
    size: int
    zimcheck_result: dict[str, Any]
    zim_metadata: dict[str, Any]
    events: list[str]
    current_locations: list[BookLocationSchema]
    target_locations: list[BookLocationSchema]


class WarehousePathSchema(BaseModel):
    """
    Schema for reading warehouse path with warehouse information
    """

    path_id: UUID
    folder_name: str
    warehouse_id: UUID
    warehouse_name: str


class UserSchema(BaseModel):
    """
    Schema for reading a user model
    """

    username: str
    role: str
    scope: dict[str, dict[str, bool]]
