from fastapi import APIRouter, Depends, Response
from fastapi_pagination import Page, Params, paginate

from backend.digesters.raw import DigesterRaw
from backend.schemas import DigestersListSchema

router = APIRouter(
    prefix="/digesters",
    tags=["digesters"],
)


@router.get(
    "",
    response_model=Page[DigestersListSchema],
    status_code=200,
    tags=["digesters"],
)
async def list_digesters(params: Params = Depends()):
    return paginate(
        [DigestersListSchema(slug="raw", description=DigesterRaw.description)],
        params,
    )


class XMLResponse(Response):
    media_type = "application/xml"


@router.get(
    "/raw",
    status_code=200,
    tags=["digesters"],
    response_class=XMLResponse,
)
async def raw():
    return Response(
        content=await DigesterRaw.generate(),
        media_type="application/xml",
    )
