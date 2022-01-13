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


class BooksListSendSchema(BaseModel):
    id: uuid.UUID
    name: str


class TitlesListSendSchema(BaseModel):
    ident: str


class TitleSendSchema(BaseModel):

    ident: str
    languages: List[str]
    tags: List[str]
    metadata: Dict[str, Any]
    books: List[BooksListSendSchema]


class Message(BaseModel):
    message: str
