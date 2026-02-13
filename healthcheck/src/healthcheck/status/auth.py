import datetime

from pydantic import BaseModel

from healthcheck.context import Context
from healthcheck.status import Result
from healthcheck.status.requests import query_api


class Token(BaseModel):
    """Access token on successful authentication."""

    access_token: str
    expires_time: datetime.datetime
    refresh_token: str
    token_type: str = "Bearer"


async def authenticate() -> Result[Token]:
    """Check if authentication is sucessful with CMS"""
    response = await query_api(
        f"{Context.cms_api_url}/auth/authorize",
        method="POST",
        payload={"username": Context.cms_username, "password": Context.cms_password},
        check_name="cms-api-authentication",
    )
    return Result(
        success=response.success,
        status_code=response.status_code,
        data=Token.model_validate(response.json) if response.success else None,
    )
