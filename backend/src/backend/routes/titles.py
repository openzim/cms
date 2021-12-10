from fastapi import APIRouter

from backend.models import Title, database
from backend.schemas import TitleSendSchema, TitlesListSendSchema

router = APIRouter(
    prefix="/titles",
    tags=["titles"],
)


@database.transaction()
@router.get("", status_code=200, tags=["titles"], response_model=TitlesListSendSchema)
async def list_titles():
    titles = await Title.objects.fields("ident").all()
    return {"titles": titles}


@database.transaction()
@router.get(
    "/{ident}", status_code=200, tags=["titles"], response_model=TitleSendSchema
)
async def get_title(ident: str):
    title = await Title.objects.select_all().get(ident=ident)
    return title
