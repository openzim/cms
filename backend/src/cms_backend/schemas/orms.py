from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

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
    producer_unique_id: str
    producer_display_name: str | None
    producer_display_url: str | None


class WarehousePathInfoSchema(BaseModel):
    """
    Schema for warehouse path information (with warehouse details)
    """

    path_id: UUID
    folder_name: str
    warehouse_name: str


class TitleFullSchema(TitleLightSchema):
    """
    Schema for reading a title model with all fields including books
    """

    dev_warehouse_paths: list[WarehousePathInfoSchema]
    prod_warehouse_paths: list[WarehousePathInfoSchema]
    in_prod: bool
    events: list[str]
    books: list["BookLightSchema"]


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


class ProducerSchema(BaseModel):
    """
    Schema for producer information
    """

    display_name: str
    display_url: str
    unique_id: str


class BookLocationSchema(BaseModel):
    """
    Schema for book location information
    """

    warehouse_path_id: UUID
    warehouse_name: str
    folder_name: str
    filename: str
    status: str  # 'current' or 'target'


class BookLightSchema(BaseModel):
    """
    Schema for reading a book model with some fields
    """

    id: UUID
    title_id: UUID | None
    status: str
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
    producer: ProducerSchema
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
