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
            "MEDIA_COUNT_INCREASE_THRESHOLD": Context.media_count_increase_threshold,
            "ARTICLE_COUNT_INCREASE_THRESHOLD": (
                Context.article_count_increase_threshold
            ),
            "MEDIA_COUNT_DECREASE_THRESHOLD": Context.media_count_decrease_threshold,
            "ARTICLE_COUNT_DECREASE_THRESHOLD": (
                Context.article_count_decrease_threshold
            ),
            "ZIM_TITLE_MAX_LENGTH": Context.zim_title_max_length,
            "ZIM_DESCRIPTION_MAX_LENGTH": Context.zim_description_max_length,
        },
        status_code=HTTPStatus.OK,
    )
