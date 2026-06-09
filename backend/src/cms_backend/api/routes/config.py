from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from cms_backend.context import Context

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config() -> JSONResponse:
    """Get the configuration settings and values defined by the API"""
    return JSONResponse(
        content={
            "MEDIA_COUNT_CHANGE_THRESHOLD": Context.media_count_change_threshold,
            "ARTICLE_COUNT_CHANGE_THRESHOLD": Context.article_count_change_threshold,
        },
        status_code=HTTPStatus.OK,
    )
