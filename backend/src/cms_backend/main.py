import os
from collections import defaultdict
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from cms_backend.utils.database import (
    upgrade_db_schema,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    upgrade_db_schema()
    yield


def create_app(*, debug: bool = True):
    app = FastAPI(
        debug=debug,
        docs_url="/",
        title="CMS API",
        version="1.0.0",
        description="CMS API for managing titles, books, and other resources",
        lifespan=lifespan,
    )

    if origins := os.getenv("ALLOWED_ORIGINS", None):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins.split(","),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    main_router = APIRouter(prefix="/v2")

    app.include_router(router=main_router)

    return app


app = create_app()


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_, exc: RequestValidationError):
    # transform the pydantic validation errors to a dictionary mapping
    # the field to the list of errors
    errors: dict[str | int, list[str]] = defaultdict(list)
    for err in exc.errors():
        loc = err["loc"]
        key = loc[-1] if loc else "root"  # fallback for model level errors
        errors[key].append(err["msg"])

    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Input values failed constraints validation",
            "errors": errors,
        },
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(_, exc: ValidationError):
    # transform the pydantic validation errors to a dictionary mapping
    # the field to the list of errors
    errors: dict[str | int, list[str]] = defaultdict(list)
    for err in exc.errors():
        loc = err["loc"]
        key = loc[-1] if loc else "root"  # fallback for model level errors
        errors[key].append(err["msg"])
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Input values failed constraints validation",
            "errors": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code, content={"success": False, "message": exc.detail}
    )


@app.exception_handler(Exception)
async def generic_error_handler(_, __):  # pyright: ignore
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Internal server error"},
    )
