import asyncio
from collections.abc import Coroutine
from http import HTTPStatus
from pathlib import Path
from typing import Any
from uuid import UUID

import aiohttp
from pydantic import BaseModel

from healthcheck.context import Context
from healthcheck.status import Result
from healthcheck.status import status_logger as logger
from healthcheck.status.requests import query_api


class CollectionLightSchema(BaseModel):
    """Collection for reading a collection with all the paths in it."""

    id: UUID
    name: str
    paths: list[Path]


class CollectionCatalogStatus(CollectionLightSchema):
    status: HTTPStatus


class CatalogStatus(BaseModel):
    collections: list[CollectionCatalogStatus]


async def check_collection_catalog_generation(
    session: aiohttp.ClientSession, collection: CollectionLightSchema
) -> CollectionCatalogStatus:
    async with session.get(
        f"{Context.cms_api_url}/{collection.id}/catalog.xml",
        timeout=aiohttp.ClientTimeout(total=Context.catalog_generation_timeout),
    ) as resp:
        return CollectionCatalogStatus(
            status=HTTPStatus(resp.status),
            id=collection.id,
            name=collection.name,
            paths=collection.paths,
        )


async def check_catalog_generation() -> Result[CatalogStatus]:
    """Check that generation of catalogs for all collections takes reasonable time."""
    response = await query_api(
        f"{Context.cms_api_url}/collections",
        method="GET",
        check_name="catalog-generation-status",
    )

    if not response.success:
        return Result(
            success=response.success,
            status_code=response.status_code,
            data=None,
        )

    collections = [
        CollectionLightSchema.model_validate(item)
        for item in response.json.get("items", [])
    ]
    async with aiohttp.ClientSession() as session:
        tasks: list[Coroutine[Any, Any, CollectionCatalogStatus]] = []
        for collection in collections:
            tasks.append(check_collection_catalog_generation(session, collection))

        catalog_statuses = await asyncio.gather(*tasks)
        failures = [
            catalog_status
            for catalog_status in catalog_statuses
            if catalog_status.status != HTTPStatus.OK
        ]
        if failures:
            logger.error(
                f"Failed to generate catalogs for the following collections: "
                f"{','.join([failure.name for failure in failures])}"
            )

        return Result(
            success=bool(failures),
            status_code=HTTPStatus.OK if len(failures) > 0 else HTTPStatus.NOT_FOUND,
            data=CatalogStatus(collections=catalog_statuses),
        )
