import datetime

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/test",
    tags=["test"],
)


@router.get("/{timestamp}")
async def test(timestamp: int):
    """placeholder test route"""
    received_on: datetime.datetime = datetime.datetime.now()
    try:
        requested_on: datetime.datetime = datetime.datetime.fromtimestamp(timestamp)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid timestamp: {exc}"
        ) from exc

    return {"requested_on": requested_on, "received_on": received_on}
