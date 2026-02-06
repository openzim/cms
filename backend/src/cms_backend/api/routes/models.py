import math
from typing import Generic, TypeVar

from pydantic import Field

from cms_backend.schemas import BaseModel

T = TypeVar("T")


class Paginator(BaseModel):
    nb_records: int = Field(serialization_alias="count")
    skip: int
    limit: int
    page_size: int
    page: int


class ListResponse(BaseModel, Generic[T]):
    meta: Paginator
    items: list[T]


def calculate_pagination_metadata(
    *,
    nb_records: int,
    skip: int,
    limit: int,
    page_size: int,
) -> Paginator:
    page = math.floor(skip / limit) + 1 if limit > 0 else 1
    if nb_records == 0:
        return Paginator(
            nb_records=0,
            skip=skip,
            limit=limit,
            page_size=0,
            page=page,
        )
    return Paginator(
        nb_records=nb_records,
        skip=skip,
        limit=limit,
        page_size=min(page_size, nb_records),
        page=page,
    )
