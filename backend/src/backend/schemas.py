import datetime
import itertools
import uuid
from typing import Any, Dict, List, Optional, Union

import pydantic
from pydantic import BaseModel, create_model


class TagGetSchema(BaseModel):
    name: str


class LanguageGetSchema(BaseModel):
    code: str
    name: str
    native: str


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


class TitlesListSendSchemasHolder:
    """Dynamic Titles List Schemas Holder"""

    schemas = set()

    @classmethod
    def all(cls):
        return tuple(getattr(cls, name) for name in cls.schemas)

    @classmethod
    def add(cls, schema):
        setattr(cls, schema.__name__, schema)
        cls.schemas.add(schema.__name__)

    @classmethod
    def _name_for(
        cls,
        with_languages: bool = False,
        with_tags: bool = False,
        with_metadata: Union[List[str], bool] = False,
    ):
        if not with_languages and not with_tags and not with_metadata:
            return "TitlesListSendSchema"
        name = "BooksListSend"
        if with_languages:
            name += "Languages"
        if with_tags:
            name += "Tags"
        if with_metadata:
            name += "Metadata"
        name += "Schema"
        return name

    @classmethod
    def build_for(
        cls,
        with_languages: bool = False,
        with_tags: bool = False,
        with_metadata: Union[str, bool] = False,
    ):
        name = cls._name_for(
            with_languages=with_languages,
            with_tags=with_tags,
            with_metadata=with_metadata,
        )
        kwargs = {}
        if with_languages:
            kwargs["languages"] = (Optional[List[str]], ...)
        if with_tags:
            kwargs["tags"] = (Optional[List[str]], ...)
        if with_metadata:
            kwargs["metadata"] = (Optional[Dict[str, Any]], ...)
        return create_model(
            name,
            __base__=TitlesListSendSchema,
            __module__=TitlesListSendSchema.__module__,
            **kwargs,
        )

    @classmethod
    def init(cls):
        combinations = itertools.product((True, False), repeat=3)
        for kwargs in map(
            lambda r: {
                "with_languages": r[0],
                "with_tags": r[1],
                "with_metadata": r[2],
            },
            combinations,
        ):
            cls.add(cls.build_for(**kwargs))

    @classmethod
    def get_for(
        cls,
        with_languages: bool = False,
        with_tags: bool = False,
        with_metadata: Union[List[str], bool] = False,
    ):

        return getattr(
            cls,
            cls._name_for(
                with_languages=with_languages,
                with_tags=with_tags,
                with_metadata=with_metadata,
            ),
        )


class TitleSendSchema(BaseModel):

    ident: str
    languages: List[str]
    tags: List[str]
    metadata: Dict[str, Any]
    books: List[BooksListSendSchema]


class Message(BaseModel):
    message: str


TitlesListSendSchemasHolder.init()
