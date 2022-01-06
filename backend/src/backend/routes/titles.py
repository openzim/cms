import base64

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, Params, paginate
from ormar.exceptions import NoMatch

from backend.models import (
    KIND_ILLUSTRATION,
    Title,
    database,
    get_matched_m2m_combination,
)
from backend.schemas import Message, TitleSendSchema, TitlesListSendSchema

router = APIRouter(
    prefix="/titles",
    tags=["titles"],
)


@database.transaction()
@router.get(
    "", status_code=200, tags=["titles"], response_model=Page[TitlesListSendSchema]
)
async def list_titles(params: Params = Depends(), lang: str = None):
    if lang:
        if "|" in lang:
            # union of languages
            return paginate(
                (
                    await Title.objects.select_related("languages")
                    .filter(languages__code__in=lang.split("|"))
                    .fields("ident")
                    .all()
                ),
                params,
            )
        elif "," in lang:
            # intersection of languages
            idents = await get_matched_m2m_combination(
                items=lang.split(","), on="title-language"
            )
            # we could directly paginate the idents from line above but in other use
            # cases we'd probably cast and filter on it
            return paginate(
                (
                    await Title.objects.select_related("languages")
                    .filter(ident__in=idents)
                    .fields("ident")
                    .all()
                ),
                params,
            )

        # when single language code is given
        return paginate(
            (
                await Title.objects.select_related("languages")
                .filter(languages__code=lang)
                .fields("ident")
                .all()
            ),
            params,
        )
    return paginate(await Title.objects.fields("ident").all(), params)


@database.transaction()
@router.get(
    "/{ident}",
    tags=["titles"],
    response_model=TitleSendSchema,
    responses={
        404: {"model": Message, "description": "Requested Title not found"},
        200: {"model": TitleSendSchema, "description": "The requested Title"},
    },
)
async def get_title(ident: str):
    try:
        title = await Title.objects.select_all().get(ident=ident)
    except NoMatch:
        return JSONResponse(
            status_code=404, content={"message": f"Title with ID “{ident}” not found"}
        )

    return {
        "ident": title.ident,
        "languages": [lang.code for lang in title.languages],
        "tags": [tag.name for tag in title.tags],
        "metadata": {
            item.name: (
                base64.standard_b64encode(item.bin_value)
                if item.kind == KIND_ILLUSTRATION
                else item.value
            )
            for item in await title.metadata.all()
        },
        "books": [
            {"id": book.id, "name": await book.book_name()} for book in title.books
        ],
    }
