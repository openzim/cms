from uuid import UUID

from pydantic import BaseModel, Field

from healthcheck.context import Context
from healthcheck.status import Result
from healthcheck.status import status_logger as logger
from healthcheck.status.requests import query_api


class PendingBooksNeedOperation(BaseModel):
    nb_records: int
    book_ids: list[UUID] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list
    )


async def check_books_need_move() -> Result[PendingBooksNeedOperation]:
    """Check that no book with location_kind other than delete needs file operation."""

    check_name = "cms-need-book-move"

    response = await query_api(
        f"{Context.cms_api_url}/books",
        method="GET",
        params={
            "limit": 1,
            "location_kinds": ["quarantine", "staging"],
            "needs_file_operation": "true",
        },
        check_name=check_name,
    )
    if not response.success:
        return Result(
            success=response.success,
            status_code=response.status_code,
            data=None,
        )

    items = response.json.get("items", [])
    if not items:
        logger.info(
            "No books need move operation.",
            extra={"checkname": check_name},
        )
        return Result(
            success=response.success,
            status_code=response.status_code,
            data=PendingBooksNeedOperation(nb_records=0),
        )

    return Result(
        success=False,
        status_code=response.status_code,
        data=PendingBooksNeedOperation(
            nb_records=response.json.get("meta", {}).get("count", 0),
            book_ids=[UUID(item["id"]) for item in items],
        ),
    )


async def check_books_need_deletion() -> Result[PendingBooksNeedOperation]:
    """Check that no book with location_kind delete needs file operation."""

    check_name = "cms-need-book-delete"

    response = await query_api(
        f"{Context.cms_api_url}/books",
        method="GET",
        params={
            "limit": 1,
            "location_kinds": ["to_delete"],
            "needs_file_operation": "true",
        },
        check_name=check_name,
    )
    if not response.success:
        return Result(
            success=response.success,
            status_code=response.status_code,
            data=None,
        )

    items = response.json.get("items", [])
    if not items:
        logger.info(
            "No books need delete operation.",
            extra={"checkname": check_name},
        )
        return Result(
            success=response.success,
            status_code=response.status_code,
            data=PendingBooksNeedOperation(nb_records=0),
        )

    return Result(
        success=False,
        status_code=response.status_code,
        data=PendingBooksNeedOperation(
            nb_records=response.json.get("meta", {}).get("count", 0),
            book_ids=[UUID(item["id"]) for item in items],
        ),
    )
