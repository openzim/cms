from fastapi import APIRouter, Depends
from fastapi_pagination import Page, Params, paginate

from backend.models import Title, database
from backend.schemas import TitleSendSchema, TitlesListSendSchema

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
    "/{ident}", status_code=200, tags=["titles"], response_model=TitleSendSchema
)
async def get_title(ident: str):
    title = await Title.objects.select_all().get(ident=ident)
    return title
