from dataclasses import dataclass
from http import HTTPStatus
from json import JSONDecodeError
from typing import Any
from uuid import UUID

import requests

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.requested_task import create_zimfarm_task_info
from cms_backend.schemas.models import TaskInfo


@dataclass
class Response:
    """A response from the webapi"""

    status_code: int
    success: bool
    json: dict[str, Any]


def query_api(
    url: str,
    method: str = "get",
    *,
    headers: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = Context.requests_timeout,
) -> Response:
    req_headers: dict[str, Any] = {}

    req_headers.update(  # pyright: ignore[reportUnknownMemberType]
        headers if headers else {}
    )
    func = {
        "GET": requests.get,
        "POST": requests.post,
        "PATCH": requests.patch,
        "DELETE": requests.delete,
        "PUT": requests.put,
    }.get(method.upper(), requests.get)

    resp = None
    try:
        resp = func(
            url, headers=req_headers, json=payload, params=params, timeout=timeout
        )
        return Response(
            status_code=resp.status_code,
            success=resp.ok,
            json=resp.json() if resp.text and resp.text.strip() else {},
        )
    except (JSONDecodeError, Exception) as exc:
        logger.exception(
            f"unexpected error while making request to {url} : "
            f"{resp.text if resp else exc}"
        )
        return Response(
            status_code=resp.status_code if resp else -1,
            success=resp.ok if resp else False,
            json={},
        )


def fetch_task_from_zimfarm(task_id: UUID) -> TaskInfo:
    response = query_api(method="GET", url=f"{Context.zimfarm_api_url}/tasks/{task_id}")
    if response.status_code == HTTPStatus.NOT_FOUND:
        # if it fails, try to find the requested task
        response = query_api(
            method="GET", url=f"{Context.zimfarm_api_url}/requested-tasks/{task_id}"
        )
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise RecordDoesNotExistError(
            "Task with ID {task_id} does not exist on Zimfarm"
        )
    elif response.status_code != HTTPStatus.OK:
        raise ValueError(
            f"Failed to find task on Zimfarm with HTTP {response.status_code}\n",
            f"{response.json.get('message')}",
        )
    return create_zimfarm_task_info(response.json)
