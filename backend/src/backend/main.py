#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend import __description__, __title__, __version__
from backend.constants import BackendConf
from backend.models import database
from backend.routes import ZimcheckDashboard, books, exports, languages, tags, titles

PREFIX = "/v1"


async def startup() -> None:
    if not database.is_connected:
        await database.connect()


async def shutdown() -> None:
    if database.is_connected:
        await database.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title=__title__,
        description=__description__,
        version=__version__,
        on_startup=[startup],
        on_shutdown=[shutdown],
    )
    app.state.database = database

    @app.get("/")
    async def landing():
        """Redirect to root of latest version of the API"""
        return RedirectResponse(f"{PREFIX}/", status_code=308)

    api = FastAPI(
        title=__title__,
        description=__description__,
        version=__version__,
        docs_url="/",
        openapi_tags=[
            {
                "name": "exports",
                "description": "Kiwix public exporter",
            },
            {
                "name": "titles",
                "description": "Library Entries which group Books together",
            },
            {
                "name": "books",
                "description": "Individual, potentially flavoured ZIM files",
            },
            {
                "name": "tags",
                "description": "ZIM Tags for Titles and Books",
            },
            {
                "name": "languages",
                "description": "Languages for Titles and Books",
            },
            {
                "name": "dashboard",
                "description": "Condensed stats of zimcheck data",
            },
        ],
        contact={
            "name": "Kiwix/openZIM Team",
            "url": "https://www.kiwix.org/en/contact/",
            "email": "contact+cms@kiwix.org",
        },
        license_info={
            "name": "GNU General Public License v3.0",
            "url": "https://www.gnu.org/licenses/gpl-3.0.en.html",
        },
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=BackendConf.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api.include_router(router=exports.router)
    api.include_router(router=books.router)
    api.include_router(router=languages.router)
    api.include_router(router=tags.router)
    api.include_router(router=titles.router)
    api.include_router(router=ZimcheckDashboard.router)

    app.mount(PREFIX, api)

    return app
