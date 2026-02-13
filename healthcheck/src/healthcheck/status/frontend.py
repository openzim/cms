import re
from http import HTTPStatus

import aiohttp
from pydantic import BaseModel

from healthcheck.context import Context
from healthcheck.status import Result
from healthcheck.status import status_logger as logger


class FrontendInfo(BaseModel):
    """Information about the frontend availability."""

    url: str
    status: str
    has_valid_title: bool


async def check_frontend() -> Result[FrontendInfo]:
    """Check if the CMS frontend is accessible and working correctly.

    Checks:
    - No SSL issues (valid certificate)
    - HTTP status code is 200
    - Content is an HTML document
    - HTML document title is "CMS"
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                Context.cms_frontend_url,
                timeout=aiohttp.ClientTimeout(total=Context.requests_timeout),
            ) as resp:
                # Check status code
                if resp.status != HTTPStatus.OK:
                    logger.warning(
                        f"Frontend returned status code {resp.status} instead of 200",
                        extra={"checkname": "cms-frontend-status"},
                    )
                    return Result(
                        success=False,
                        status_code=HTTPStatus(resp.status),
                        data=FrontendInfo(
                            url=Context.cms_frontend_url,
                            status=f"HTTP {resp.status}",
                            has_valid_title=False,
                        ),
                    )

                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type.lower():
                    logger.warning(
                        f"Frontend returned Content-Type '{content_type}' "
                        "instead of text/html",
                        extra={"checkname": "cms-frontend-status"},
                    )
                    return Result(
                        success=False,
                        status_code=HTTPStatus.OK,
                        data=FrontendInfo(
                            url=Context.cms_frontend_url,
                            status="Not HTML content",
                            has_valid_title=False,
                        ),
                    )

                text = await resp.text()
                title_match = re.search(r"<title>CMS</title>", text)

                if not title_match:
                    logger.warning(
                        "Frontend HTML does not contain expected title",
                        extra={"checkname": "cms-frontend-status"},
                    )
                    return Result(
                        success=False,
                        status_code=HTTPStatus.OK,
                        data=FrontendInfo(
                            url=Context.cms_frontend_url,
                            status="Invalid title",
                            has_valid_title=False,
                        ),
                    )

                return Result(
                    success=True,
                    status_code=HTTPStatus.OK,
                    data=FrontendInfo(
                        url=Context.cms_frontend_url,
                        status="online",
                        has_valid_title=True,
                    ),
                )

    except aiohttp.ClientSSLError as e:
        logger.exception(
            "SSL error when connecting to frontend",
            extra={"checkname": "cms-frontend-status"},
        )
        return Result(
            success=False,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            data=FrontendInfo(
                url=Context.cms_frontend_url,
                status=f"SSL error: {e!s}",
                has_valid_title=False,
            ),
        )
    except aiohttp.ClientError as e:
        logger.exception(
            "Client error when connecting to frontend",
            extra={"checkname": "cms-frontend-status"},
        )
        return Result(
            success=False,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            data=FrontendInfo(
                url=Context.cms_frontend_url,
                status=f"Connection error: {e!s}",
                has_valid_title=False,
            ),
        )
    except Exception:
        logger.exception(
            "Unexpected error when checking frontend",
            extra={"checkname": "cms-frontend-status"},
        )
        return Result(
            success=False,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            data=FrontendInfo(
                url=Context.cms_frontend_url,
                status="offline",
                has_valid_title=False,
            ),
        )
