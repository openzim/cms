import datetime
import uuid
from typing import Any, Dict, List

import pydantic
from pydantic import BaseModel


class BookAddSchema(BaseModel):
    id: uuid.UUID
    period: datetime.date
    counter: Dict[str, Any]
    article_count: int
    media_count: int
    size: int
    metadata: Dict[str, Any]
    url: pydantic.HttpUrl
    zimcheck: Dict[str, Any]


class TitlesListSendSchema(BaseModel):
    ident: str


class TitleSendSchema(BaseModel):
    class Books(BaseModel):
        id: uuid.UUID
        name: str

    ident: str
    languages: List[str]
    tags: List[str]
    metadata: Dict[str, Any]
    books: List[Books]
