#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend import __description__, __title__, __version__
from backend.constants import BackendConf

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


app.mount(PREFIX, api)
