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
    class TitleSendSchema(BaseModel):
        ident: str

    titles: List[TitleSendSchema]


class TitleSendSchema(BaseModel):
    class LanguageSendSchema(BaseModel):
        code: str

    class BookTagSendSchema(BaseModel):
        name: str

    ident: str
    languages: List[LanguageSendSchema]
    tags: List[BookTagSendSchema]
