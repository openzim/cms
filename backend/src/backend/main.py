#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import base64
import datetime
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from zimscraperlib.i18n import find_language_names

from backend import __description__, __title__, __version__
from backend.constants import BackendConf
from backend.models import (
    KIND_ILLUSTRATION,
    KIND_TEXT,
    Book,
    BookMetadata,
    BookTag,
    Language,
    Title,
    TitleMetadata,
    database,
)
from backend.schemas import BookAddSchema, TitleSendSchema, TitlesListSendSchema
from backend.utils import get_ident_from_name

PREFIX = "/v1"

app = FastAPI(title=__title__, description=__description__, version=__version__)


@app.get("/")
async def landing():
    """Redirect to root of latest version of the API"""
    return RedirectResponse(f"{PREFIX}/", status_code=308)


api = FastAPI(title=__title__, description=__description__, version=__version__)

api.add_middleware(
    CORSMiddleware,
    allow_origins=BackendConf.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/")
async def root():
    """Greetings"""
    return "Hello World"


@api.get("/test/{timestamp}")
async def test(timestamp: int):
    """placeholder test route"""
    received_on: datetime.datetime = datetime.datetime.now()
    try:
        requested_on: datetime.datetime = datetime.datetime.fromtimestamp(timestamp)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp: {exc}")

    return {"requested_on": requested_on, "received_on": received_on}


@database.transaction()
@api.post("/books/add/", status_code=201)
async def add_book(book_payload: BookAddSchema):
    """API endpoint to receive Book addition requests and add to database"""

    try:
        title = await Title.objects.get_or_create(
            ident=get_ident_from_name(book_payload.metadata["Name"])
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Name metadata. Unable to build Title identifier: {exc}",
        ) from exc

    book = await Book.objects.create(
        id=book_payload.id,
        counter=book_payload.counter,
        period=book_payload.period,
        article_count=book_payload.article_count,
        media_count=book_payload.media_count,
        size=book_payload.size,
        url=book_payload.url,
        zimcheck=book_payload.zimcheck,
    )

    await book.update(title=title)

    for metadata_name, value in book_payload.metadata.items():
        if metadata_name.startswith("Illustration_"):
            await BookMetadata.objects.create(
                book=book.id,
                name=metadata_name,
                bin_value=base64.standard_b64decode(value),
                kind=KIND_ILLUSTRATION,
            )
        else:
            await BookMetadata.objects.create(
                book=book.id,
                name=metadata_name,
                value=value,
                kind=KIND_TEXT,
            )

    for metadata in await book.metadata.all():
        await TitleMetadata.objects.create(
            title=title.ident,
            name=metadata.name,
            bin_value=metadata.bin_value,
            value=metadata.value,
            kind=metadata.kind,
        )

    for tag_name in book_payload.metadata["Tags"].split(";"):
        book_tag = await BookTag.objects.get_or_create(name=tag_name)
        await book.tags.add(book_tag)
        if not re.match(r"_(sw|ftindex|pictures|videos|details):(yes|no)", tag_name):
            await title.tags.add(book_tag)

    for lang_code in book_payload.metadata["Language"].split(","):
        native_name, english_name = find_language_names(lang_code)
        language = await Language.objects.get_or_create(
            code=lang_code, name=english_name, native=native_name
        )
        await book.languages.add(language)
        await title.languages.add(language)

    return {"msg": "ok", "uuid": str(book.id), "title": book.title.ident}


@database.transaction()
@api.get("/titles/", status_code=200, response_model=TitlesListSendSchema)
async def receive_titles():
    titles = await Title.objects.select_all().all()
    return {"titles": titles}


@database.transaction()
@api.get("/titles/{ident}", status_code=200, response_model=TitleSendSchema)
async def receive_title(ident: str):
    title = await Title.objects.select_related(["languages", "tags"]).get(ident=ident)
    return title


app.mount(PREFIX, api)
