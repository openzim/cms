from fastapi import APIRouter, Response

from backend.digesters.raw import gen_raw_digester

router = APIRouter(
    prefix="/digesters",
    tags=["digesters"],
)


@router.get("/raw", status_code=200)
async def raw():
    return Response(
        content=await gen_raw_digester(),
        media_type="application/xml",
    )
