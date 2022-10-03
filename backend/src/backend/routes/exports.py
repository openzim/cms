from fastapi import APIRouter

from backend.exporters.kiwix_public_exporter import KiwixPublicExporter
from backend.models import database

router = APIRouter(
    prefix="/export",
    tags=["exports"],
)


@router.get(
    "",
    status_code=200,
    tags=["exports"],
    responses={
        200: {
            "description": "Kiwix public Exporter",
        },
    },
)
@database.transaction()
async def export():  # pragma: no cover
    return await KiwixPublicExporter.export()
