#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import base64
import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from zimscraperlib.i18n import get_language_details

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
    database,
)
from backend.schemas import BookAddSchema
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

    title = await Title.objects.get_or_create(
        ident=get_ident_from_name(book_payload.metadata["Name"])
    )
    await book.update(title=title)

    for tag_name in book_payload.metadata["Tags"].split(";"):
        book_tag = await BookTag.objects.get_or_create(name=tag_name)
        await book.tags.add(book_tag)
        await title.tags.add(book_tag)

    for lang_code in book_payload.metadata["Language"].split(","):
        lang_dict = get_language_details(lang_code)
        language = await Language.objects.get_or_create(
            code=lang_code, name=lang_dict["english"], native=lang_dict["native"]
        )
        await book.languages.add(language)
        await title.languages.add(language)

    return {"msg": "ok", "ident": book.title.ident}


app.mount(PREFIX, api)
