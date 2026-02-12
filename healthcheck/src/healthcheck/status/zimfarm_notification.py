from uuid import UUID

from pydantic import BaseModel, Field

from healthcheck.context import Context
from healthcheck.status import Result
from healthcheck.status import status_logger as logger
from healthcheck.status.requests import query_api


class PendingZimfarmNotifications(BaseModel):
    nb_records: int
    notification_ids: list[UUID] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list
    )


async def check_zimfarm_notifications_processed() -> (
    Result[PendingZimfarmNotifications]
):
    """Check that no zimfarm notifications stuck in pending state."""
    check_name = "cms-pending-zimfarm-notifications"
    response = await query_api(
        f"{Context.cms_api_url}/zimfarm-notifications",
        method="GET",
        params={"limit": 1, "status": "pending"},
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
            "No zimfarm notifications are in pending state",
            extra={"checkname": check_name},
        )
        return Result(
            success=response.success,
            status_code=response.status_code,
            data=PendingZimfarmNotifications(nb_records=0),
        )
    return Result(
        success=False,
        status_code=response.status_code,
        data=PendingZimfarmNotifications(
            nb_records=response.json.get("meta", {}).get("count", 0),
            notification_ids=[UUID(item["id"]) for item in items],
        ),
    )
