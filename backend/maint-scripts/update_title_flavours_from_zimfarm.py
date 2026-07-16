#!/usr/bin/env python3
"""Maintenance script to populate CMS database with recipes and title flavours from
zimfarm API.

This script is idempotent and can be run multiple times without creating duplicates.
It
- Finds all recipes on Zimfarm API
- Fetches all the successful tasks for the recipe
- For each task
    - Find a title with the same name from the tasks' file information
    - Find a title flavour for the title and associates it with the recipe
    - If existing flavour differs from current recipe, warning messages are logged

Environment variables required:
- ZIMFARM_API_URL: URL of Zimfarm API to fetch recipes and tasks from

"""

import os
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any
from uuid import UUID

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm.attributes import flag_modified

from cms_backend import logger
from cms_backend.db import Session
from cms_backend.db.flavour import get_title_flavour_or_none
from cms_backend.db.models import Book
from cms_backend.db.title import get_title_by_name_or_none
from cms_backend.utils.zim import get_missing_keys


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
    timeout: int = 30,
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


def process_task(
    session: OrmSession,
    *,
    task: dict[str, Any],
    zf_recipe: dict[str, Any],
    zimfarm_api_url: str,
):
    response = query_api(f"{zimfarm_api_url}/tasks/{task['id']}")
    if not response.success:
        logger.error(
            f"Unable to fetch task {task['id']} from {zimfarm_api_url}: {response.json}"
        )
        return

    for filename in response.json.get("files", {}):
        metadata = response.json["files"][filename].get("info", {}).get("metadata", {})
        missing_keys = get_missing_keys(metadata, "Name")
        if missing_keys:
            logger.warning(
                f"Task {task['id']} metadata is missing keys: {','.join(missing_keys)}"
            )
            continue

        title = get_title_by_name_or_none(session, name=metadata["Name"])
        if title is None:
            logger.debug(
                f"Title with name '{metadata['Name']}' from task {task['id']} "
                "does not yet exist on CMS"
            )
            continue

        flavour = metadata.get("Flavour", "")
        flavour = flavour[1:] if flavour.startswith("_") else flavour

        tf = get_title_flavour_or_none(session, title.id, flavour)
        if tf is None:
            logger.warning(
                f"Title flavour '{flavour}' does not exist for title '{title.name}'"
            )
            continue

        if tf.recipe_id is None:
            tf.recipe_id = UUID(zf_recipe["id"])
            session.add(tf)

        elif tf.recipe_id != UUID(zf_recipe["id"]):
            logger.warning(
                f"Title flavour '{tf.flavour}' for title '{title.name}' is "
                f"attached to a different recipe from zimfarm {zf_recipe['name']}"
            )

        # update books notifications whose flavour matches
        books = session.scalars(
            select(Book).where(
                Book.flavour == flavour,
                Book.title_id == title.id,
                Book.recipe_id.is_(None),
            )
        ).all()
        for book in books:
            book.recipe_id = tf.recipe_id
            if book.zimfarm_notification and get_missing_keys(
                book.zimfarm_notification.content, "recipe_id"
            ):
                zimfarm_notification = book.zimfarm_notification
                zimfarm_notification.content["recipe_id"] = zf_recipe["id"]
                flag_modified(zimfarm_notification, "content")


def process_recipe(
    session: OrmSession,
    zf_recipe: dict[str, Any],
    zimfarm_api_url: str,
):
    skip = 0
    limit = 50
    while True:
        response = query_api(
            f"{zimfarm_api_url}/tasks",
            params={
                "skip": skip,
                "limit": limit,
                "status": ["succeeded"],
                "recipe_id": zf_recipe["id"],
                "sort_criteria": "done",
            },
        )
        if not response.success:
            logger.error(
                f"Unable to process tasks for recipe {zf_recipe['name']}: "
                f"{response.json}"
            )
            break
        tasks = response.json["items"]
        if len(tasks) == 0:
            logger.info(f"No more tasks to process for recipe {zf_recipe['name']}")
            break

        for task in tasks:
            process_task(
                session,
                task=task,
                zf_recipe=zf_recipe,
                zimfarm_api_url=zimfarm_api_url,
            )
        skip += limit


def populate_recipes_from_zimfarm(session: OrmSession, zimfarm_api_url: str):
    """Fetch recipes from zimfarm and attach CMS titles/title flavours to recipes."""
    skip = 0
    limit = 50

    while True:
        response = query_api(
            f"{zimfarm_api_url}/recipes", params={"skip": skip, "limit": limit}
        )
        if not response.success:
            logger.error(
                f"Unable to fetch recipes from {zimfarm_api_url}: {response.json}. "
                "Exiting..."
            )
            break
        zf_recipes = response.json["items"]
        if len(zf_recipes) == 0:
            logger.info(f"No more recipes returned from {zimfarm_api_url}")
            break
        for zf_recipe in zf_recipes:
            process_recipe(session, zf_recipe, zimfarm_api_url)
            session.commit()
        skip += limit


def main():

    zimfarm_api_url = os.getenv("ZIMFARM_API_URL", "https://api.farm.openzim.org/v2")
    with Session() as session:
        populate_recipes_from_zimfarm(session, zimfarm_api_url)


if __name__ == "__main__":
    main()
