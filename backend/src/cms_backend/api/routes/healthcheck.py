from fastapi import APIRouter
from fastapi.responses import JSONResponse

from cms_backend.utils.datetime import getnow

router = APIRouter(prefix="/healthcheck", tags=["healthcheck"])


@router.get("")
def get_health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "timestamp": getnow().isoformat()})
