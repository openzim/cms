import os

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse
from fastapi_pagination import Page, Params, paginate

from backend.digesters.raw import Digester
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
        [DigestersListSchema(slug="raw", description=Digester.description)],
        params,
    )


class XMLResponse(Response):
    media_type = "application/xml"


@router.get("/raw/", status_code=200, tags=["digesters"])
def get_raw():
    return dict(slug="raw", description=Digester.description)


@router.get(
    "/raw/trigger",
    status_code=200,
    tags=["digesters"],
)
async def trigger_raw():
    if Digester.status != "building":
        await Digester.generate()
    return {"message": "OK"}


@router.get(
    "/raw/library.xml", status_code=200, tags=["digesters"], response_class=XMLResponse
)
def get_raw_library():
    try:
        return FileResponse(path=os.getcwd() + "/" + "digesters_dump/raw.xml")
    except RuntimeError:
        return 404
