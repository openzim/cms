from fastapi import APIRouter, Depends, Response
from fastapi_pagination import Page, Params, paginate

from backend.digesters.raw import description as raw_description
from backend.digesters.raw import gen_raw_digester
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
        [DigestersListSchema(slug="raw", description=raw_description)],
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
        content=await gen_raw_digester(),
        media_type="application/xml",
    )
