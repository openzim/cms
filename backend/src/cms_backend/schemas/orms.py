from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T")


class ListResult(BaseModel, Generic[T]):
    nb_records: int
    records: list[T]


class TitleLightSchema(BaseModel):
    """
    Schema for reading a title model with some fields
    """

    name: str


class ZimfarmNotificationLightSchema(BaseModel):
    """
    Schema for reading a zimfarm notification model with some fields
    """

    id: UUID
    book_id: UUID | None
    processed: bool
    errored: bool
    received_at: datetime


class ZimfarmNotificationFullSchema(ZimfarmNotificationLightSchema):
    content: dict[str, Any]
    events: list[str]
