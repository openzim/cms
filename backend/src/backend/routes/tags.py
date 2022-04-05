from fastapi import APIRouter, Depends
from fastapi_pagination import Page, Params, paginate

from backend.models import TitleTag, database

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
)


@router.get(
    "",
    status_code=200,
    tags=["tags"],
    responses={
        200: {
            "model": Page[str],
            "description": "Tags list",
        },
    },
)
@database.transaction()
async def list_tags(params: Params = Depends()):
    def dress_page(page):
        page.items = [item.name for item in page.items]
        return page

    return dress_page(
        paginate(
            await TitleTag.objects.order_by("name").all(),
            params,
        )
    )
