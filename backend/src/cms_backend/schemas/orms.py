from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ListResult(BaseModel, Generic[T]):
    nb_records: int
    records: list[T]


class TitleLightSchema(BaseModel):
    """
    Schema for reading a schedule model with some fields
    """

    name: str
