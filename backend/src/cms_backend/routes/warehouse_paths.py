from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import gen_dbsession
from cms_backend.db.warehouse_path import get_warehouse_paths as db_get_warehouse_paths
from cms_backend.schemas.orms import WarehousePathSchema

router = APIRouter(prefix="/warehouse-paths", tags=["warehouse-paths"])


@router.get("")
async def get_warehouse_paths(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> list[WarehousePathSchema]:
    """Get all warehouse paths with warehouse information"""

    return db_get_warehouse_paths(session)
