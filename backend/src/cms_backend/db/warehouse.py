from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Warehouse
from cms_backend.schemas.orms import ListResult


def get_warehouse_or_none(session: OrmSession, warehouse_name: str) -> Warehouse | None:
    """Get a warehouse by name or None."""
    return session.scalars(
        select(Warehouse).where(Warehouse.name == warehouse_name)
    ).one_or_none()


def get_warehouse(session: OrmSession, warehouse_name: str) -> Warehouse:
    """Get a warehouse by name if possible else raise an exception"""
    if (
        warehouse := get_warehouse_or_none(session, warehouse_name=warehouse_name)
    ) is None:
        raise RecordDoesNotExistError(
            f"Warehouse with name {warehouse_name} does not exist"
        )
    return warehouse


def get_warehouses(
    session: OrmSession, *, name: str | None = None, skip: int, limit: int
) -> ListResult[str]:
    """Get the list of warehouses."""
    stmt = (
        select(func.count().over().label("nb_records"), Warehouse.name)
        .where(
            # If a client provides an argument i.e it is not None,
            # we compare the corresponding model field against the argument,
            # otherwise, we compare the argument to its default which translates
            # to a SQL true i.e we don't filter based on this argument (a no-op).
            (
                Warehouse.name.ilike(f"%{name if name is not None else ''}%")
                | (name is None)
            ),
        )
        .offset(skip)
        .limit(limit)
        .order_by(Warehouse.name.desc())
    )
    results = ListResult[str](nb_records=0, records=[])

    for nb_records, warehouse_name in session.execute(stmt).all():
        results.nb_records = nb_records
        results.records.append(warehouse_name)
    return results
