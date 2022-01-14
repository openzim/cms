import base64

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, Params, paginate
from ormar.exceptions import NoMatch

from backend.models import KIND_ILLUSTRATION, Title, database
from backend.schemas import Message, TitleSendSchema, TitlesListSendSchema

router = APIRouter(
    prefix="/titles",
    tags=["titles"],
)


@database.transaction()
@router.get(
    "", status_code=200, tags=["titles"], response_model=Page[TitlesListSendSchema]
)
async def list_titles(params: Params = Depends()):
    titles = await Title.objects.fields("ident").all()
    return paginate(titles, params)


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
