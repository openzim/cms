from fastapi import APIRouter, Depends
from fastapi_pagination import Page, Params, paginate

from backend.models import Language, database
from backend.schemas import LanguageGetSchema

router = APIRouter(
    prefix="/languages",
    tags=["languages"],
)


@database.transaction()
@router.get(
    "",
    status_code=200,
    tags=["languages"],
    responses={
        200: {
            "model": Page[LanguageGetSchema],
            "description": "Languages list",
        },
    },
)
async def list_languages(params: Params = Depends()):
    def dress_page(page):
        for index, item in enumerate(page.items):
            page.items[index] = LanguageGetSchema(
                **{"code": item.code, "name": item.name, "native": item.native}
            )

        return page

    return dress_page(
        paginate(
            await Language.objects.exclude_fields(["books", "titles"])
            .order_by("code")
            .all(),
            params,
        )
    )
