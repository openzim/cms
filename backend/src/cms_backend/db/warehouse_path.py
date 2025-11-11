from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Warehouse, WarehousePath
from cms_backend.schemas.orms import WarehousePathSchema


def get_warehouse_paths(session: OrmSession) -> list[WarehousePathSchema]:
    """Get all warehouse paths with their warehouse information"""

    stmt = (
        select(
            WarehousePath.id,
            WarehousePath.folder_name,
            Warehouse.id,
            Warehouse.name,
        )
        .join(Warehouse, WarehousePath.warehouse_id == Warehouse.id)
        .order_by(Warehouse.name, WarehousePath.folder_name)
    )

    results = session.execute(stmt).all()

    return [
        WarehousePathSchema(
            path_id=path_id,
            folder_name=folder_name,
            warehouse_id=warehouse_id,
            warehouse_name=warehouse_name,
        )
        for path_id, folder_name, warehouse_id, warehouse_name in results
    ]
