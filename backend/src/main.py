#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

PREFIX = "/v1"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def noprefix_root():
    return RedirectResponse(f"{PREFIX}/", status_code=308)


@app.get(PREFIX + "/")
async def root():
    return "Hello World"


@app.get(PREFIX + "/test/{timestamp}")
async def test(timestamp: int):
    """placeholder test route"""
    received_on: datetime.datetime = datetime.datetime.now()
    try:
        requested_on: datetime.datetime = datetime.datetime.fromtimestamp(timestamp)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp: {exc}")

    return {"requested_on": requested_on, "received_on": received_on}
