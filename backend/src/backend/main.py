#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend import __description__, __title__, __version__
from backend.constants import BackendConf
from backend.routes import books, titles

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


api.include_router(router=books.router)
api.include_router(router=titles.router)

app.mount(PREFIX, api)
