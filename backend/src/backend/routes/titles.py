import base64

from fastapi import APIRouter, Depends
from fastapi_pagination import Page, Params, paginate

from backend.models import Title, TitleMetadata, database
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
    title_metadata = await TitleMetadata.objects.fields("id", "metadata").all(
        title=title.ident
    )

    return {
        "ident": title.ident,
        "languages": [lang.code for lang in title.languages],
        "tags": [tag.name for tag in title.tags],
        "metadata": {
            (elem.name): (
                elem.value if elem.value else base64.standard_b64encode(elem.bin_value)
            )
            for elem in title_metadata
        },
    }
