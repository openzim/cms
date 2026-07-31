import pathlib
from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID, uuid4

import xxhash
from botocore.exceptions import (  # pyright: ignore[reportMissingTypeStubs]
    ClientError as S3ClientError,
)
from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse, Response
from pydantic import AnyUrl, Field
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.api.context import Context as ApiContext
from cms_backend.api.routes.dependencies import (
    get_accessible_collection_ids,
    get_current_account,
    require_permission,
)
from cms_backend.api.routes.http_errors import (
    BadRequestError,
    ConflictError,
    ServerError,
)
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.api.routes.utils import build_library_xml
from cms_backend.api.token import zimfarm_client_token_provider
from cms_backend.context import Context
from cms_backend.db import collection as db_collection
from cms_backend.db import gen_dbsession
from cms_backend.db import requested_task as db_requested_task
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.models import (
    CollectionUpdateSchema,
    PartEtag,
    S3MultipartUpload,
)
from cms_backend.schemas.orms import (
    CollectionFullSchema,
    CollectionHistorySchema,
    CollectionLightSchema,
    RequestedTaskLightSchema,
)
from cms_backend.utils.requests import query_api
from cms_backend.utils.s3 import (
    complete_multipart_upload,
    generate_multipart_upload_presigned_urls,
    generate_view_presigned_url,
    get_kiwix_storage_client,
)

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionsGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None
    accessible_by: UUID | None = None
    is_private: bool | None = None


class RevertCollectionSchema(BaseModel):
    comment: NotEmptyString | None = None


@router.get("")
def get_collections(
    params: Annotated[CollectionsGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
) -> ListResponse[CollectionLightSchema]:
    """Get a list of collections"""

    results = db_collection.get_collections(
        session,
        skip=params.skip,
        limit=params.limit,
        name=params.name,
        accessible_collection_ids=accessible_collection_ids,
        accessible_by=params.accessible_by,
        is_private=params.is_private,
    )

    return ListResponse[CollectionLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


class CollectionCreateSchema(BaseModel):
    name: NotEmptyString = Field(min_length=3)
    warehouse_name: NotEmptyString = Field(min_length=3)
    is_private: bool
    download_base_url: AnyUrl | None = None
    view_base_url: AnyUrl | None = None
    article_count_increase_threshold: float | None = Field(ge=0.0, le=1.0, default=None)
    media_count_increase_threshold: float | None = Field(ge=0.0, le=1.0, default=None)
    article_count_decrease_threshold: float | None = Field(ge=0.0, le=1.0, default=None)
    media_count_decrease_threshold: float | None = Field(ge=0.0, le=1.0, default=None)


@router.post(
    "",
    dependencies=[Depends(require_permission(namespace="collection", name="create"))],
)
def create_collection(
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_account: Annotated[Account, Depends(get_current_account)],
    request: CollectionCreateSchema,
):
    """Create a collection"""
    return db_collection.create_collection_full_schema(
        db_collection.create_collection(
            session,
            author_id=current_account.id,
            name=request.name,
            warehouse_name=request.warehouse_name,
            download_base_url=(
                str(request.download_base_url)
                if request.download_base_url is not None
                else None
            ),
            view_base_url=(
                str(request.view_base_url)
                if request.view_base_url is not None
                else None
            ),
            article_count_increase_threshold=request.article_count_increase_threshold,
            article_count_decrease_threshold=request.article_count_decrease_threshold,
            media_count_increase_threshold=request.media_count_increase_threshold,
            media_count_decrease_threshold=request.media_count_decrease_threshold,
            is_private=request.is_private,
        )
    )


@router.get("/{collection_id_or_name}")
def get_collection(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
):
    """Get collection by collection ID (UUID) or name."""
    collection = db_collection.get_collection(
        session, collection_id_or_name, accessible_collection_ids
    )
    return db_collection.create_collection_full_schema(collection)


@router.patch(
    "/{collection_id_or_name}",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def update_collection(
    collection_id_or_name: Annotated[str, Path()],
    current_account: Annotated[Account, Depends(get_current_account)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    collection_data: CollectionUpdateSchema,
    session: OrmSession = Depends(gen_dbsession),
) -> CollectionFullSchema:
    """Update a collection's data"""
    return db_collection.create_collection_full_schema(
        db_collection.update_collection(
            session,
            collection_id=collection_id_or_name,
            accessible_collection_ids=accessible_collection_ids,
            request=collection_data,
            author_id=current_account.id,
        )
    )


def _get_catalog_xml_content(
    collection_id_or_name: str,
    session: OrmSession,
    path_prefix: str | None,
    accessible_collection_ids: Sequence[UUID] | None,
) -> tuple[str, int]:
    # Try to parse as UUID first, otherwise treat as name
    collection = None
    try:
        try:
            collection = db_collection.get_collection(
                session, collection_id_or_name, accessible_collection_ids
            )
        except RecordDoesNotExistError:
            pass
    except ValueError:
        # Not a valid UUID, try as name
        collection = db_collection.get_collection_by_name_or_none(
            session, collection_id_or_name, accessible_collection_ids
        )

    if collection is None:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<library version="20110515"></library>',
            HTTPStatus.NOT_FOUND,
        )

    entries = db_collection.get_latest_books_for_collection(
        session, collection.id, accessible_collection_ids
    )
    xml_content = build_library_xml(entries, path_prefix=path_prefix)

    return xml_content, HTTPStatus.OK


@router.get("/{collection_id_or_name}/catalog.xml")
def get_library_catalog_xml(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    path_prefix: Annotated[str | None, Query()] = None,
):
    """Get collection catalog as XML library by collection ID (UUID) or name."""
    xml_content, status_code = _get_catalog_xml_content(
        collection_id_or_name, session, path_prefix, accessible_collection_ids
    )
    etag = xxhash.xxh64(xml_content.encode("utf-8")).hexdigest()

    return Response(
        content=xml_content,
        status_code=status_code,
        media_type="application/xml",
        headers={"ETag": f"{etag}"},
    )


@router.head("/{collection_id_or_name}/catalog.xml")
def head_library_catalog_xml(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    path_prefix: Annotated[str | None, Query()] = None,
):
    """Get collection catalog as XML library by collection ID (UUID) or name."""
    xml_content, status_code = _get_catalog_xml_content(
        collection_id_or_name, session, path_prefix, accessible_collection_ids
    )
    etag = xxhash.xxh64(xml_content.encode("utf-8")).hexdigest()
    return Response(
        status_code=status_code,
        headers={"ETag": f"{etag}"},
        media_type="application/xml",
    )


@router.get(
    "/{collection_id_or_name}/history",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def get_collection_history(
    collection_id_or_name: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[CollectionHistorySchema]:
    results = db_collection.get_collection_history(
        session,
        collection_id=collection_id_or_name,
        skip=skip,
        limit=limit,
        accessible_collection_ids=accessible_collection_ids,
    )
    return ListResponse(
        items=results.records,
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=skip,
            limit=limit,
            page_size=len(results.records),
        ),
    )


@router.get(
    "/{collection_id_or_name}/history/{history_id}",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def get_collection_history_entry(
    collection_id_or_name: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    history_id: Annotated[UUID, Path()],
    session: OrmSession = Depends(gen_dbsession),
) -> CollectionHistorySchema:
    history_entry = db_collection.get_collection_history_entry(
        session,
        collection_id=collection_id_or_name,
        history_id=history_id,
        accessible_collection_ids=accessible_collection_ids,
    )
    return db_collection.create_collection_history_schema(history_entry)


@router.patch(
    "/{collection_id_or_name}/revert/{history_id}",
    dependencies=[Depends(require_permission(namespace="collection", name="update"))],
)
def revert_collection(
    collection_id_or_name: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    history_id: Annotated[UUID, Path()],
    request: RevertCollectionSchema,
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> JSONResponse:
    """Revert a collection to a previous history."""
    db_collection.revert_collection(
        session,
        collection_id=collection_id_or_name,
        history_id=history_id,
        author_id=current_account.id,
        comment=request.comment,
        accessible_collection_ids=accessible_collection_ids,
    )
    return JSONResponse(
        content={"message": f"collection '{collection_id_or_name}' has been restored"},
        status_code=HTTPStatus.OK,
    )


class FileUploadRequest(BaseModel):
    filename: NotEmptyString
    filesize: int = Field(ge=0)
    chunk_size: int = Field(ge=0)
    upload_id: str | None = None


@router.post(
    "/{collection_id_or_name}/upload/create",
    dependencies=[
        Depends(require_permission(namespace="collection", name="update")),
        Depends(require_permission(namespace="book", name="create")),
    ],
)
def generate_s3_presigned_urls(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    payload: FileUploadRequest,
) -> S3MultipartUpload:
    """Generate presigned URLs for upload to S3 bucket"""
    collection = db_collection.get_collection(
        session,
        collection_id_or_name,
        accessible_collection_ids=accessible_collection_ids,
    )
    s3 = get_kiwix_storage_client(Context.zim_upload_s3_bucket_uri)
    return generate_multipart_upload_presigned_urls(
        s3,
        key=f"uploads/collections/{collection.name}/{uuid4()!s}.zim",
        upload_id=payload.upload_id,
        filesize=payload.filesize,
        chunk_size=payload.chunk_size,
    )


class MultipartCompleteRequest(BaseModel):
    upload_id: str
    key: str
    parts: list[PartEtag]


class TaskCreateRequest(BaseModel):
    file: MultipartCompleteRequest


@router.post(
    "/{collection_id_or_name}/upload/complete",
    dependencies=[
        Depends(require_permission(namespace="collection", name="update")),
        Depends(require_permission(namespace="book", name="create")),
    ],
)
def compelete_zim_upload(
    collection_id_or_name: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_account: Annotated[Account, Depends(get_current_account)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    request: TaskCreateRequest,
) -> RequestedTaskLightSchema:
    """Complete ZIM upload and create task on zimfarm to process ZIM file"""
    collection = db_collection.get_collection(
        session,
        collection_id_or_name,
        accessible_collection_ids=accessible_collection_ids,
    )
    s3 = get_kiwix_storage_client(Context.zim_upload_s3_bucket_uri)
    try:
        complete_multipart_upload(
            s3,
            key=request.file.key,
            upload_id=request.file.upload_id,
            parts=request.file.parts,
        )
    except S3ClientError as exc:  # pyright: ignore[reportUnknownVariableType]
        if exc.response["Error"]["Code"] == "NoSuchUpload":
            raise ConflictError(exc.response["Error"]["Message"]) from exc
        raise exc
    flags: dict[str, Any] = {
        "download-from": generate_view_presigned_url(s3, request.file.key)
    }
    config = {
        "warehouse_path": "/other",
        "image": {
            "name": ApiContext.zimwright_image.split(":")[0],
            "tag": ApiContext.zimwright_image.split(":")[1],
        },
        "resources": {
            "cpu": ApiContext.zimtask_cpu,
            "memory": ApiContext.zimtask_memory,
            "disk": ApiContext.zimtask_disk,
            "shm": ApiContext.zimtask_memory,
            "cap_add": ["SYS_ADMIN", "NET_ADMIN"],
        },
        "platform": None,
        "monitor": False,
        "offliner": {"offliner_id": "zimwright", **flags},
    }

    ident = pathlib.Path(request.file.key).stem[:8]
    recipe_name = f"zimwright_{ident}"

    # create recipe payload
    payload: dict[str, Any] = {
        "name": recipe_name,
        "language": "eng",
        "category": "other",
        "periodicity": "manually",
        "tags": [],
        "enabled": True,
        "config": config,
        "version": ApiContext.zimwright_definition_version,
    }

    # create a unique recipe for that request on the zimfarm
    response = query_api(
        f"{Context.zimfarm_api_url}/recipes",
        method="POST",
        payload=payload,
        headers=zimfarm_client_token_provider.get_authorization_header(),
    )
    if not response.success:
        logger.error(
            f"Unable to create recipe via HTTP {response.status_code}: {response.json}"
        )
        message = (
            f"Unable to create recipe via HTTP {response.status_code}: {response.json}"
        )
        if response.status_code in [
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ]:
            # if Zimfarm replied this is a bad request, then this is most probably
            # a bad request due to user input so we can track it like a bad request
            raise BadRequestError(message)
        else:
            # otherwise, this is most probably an internal problem in our systems
            raise ServerError(message)

    recipe_id = response.json["id"]

    # request a task for that newly created recipe
    response = query_api(
        f"{Context.zimfarm_api_url}/requested-tasks",
        method="POST",
        payload={
            "recipe_names": [recipe_name],
            "worker": ApiContext.zimtask_worker,
        },
        headers=zimfarm_client_token_provider.get_authorization_header(),
    )
    if not response.success:
        logger.error(
            f"Unable to request {recipe_name} via HTTP {response.status_code}: "
            f"{response.json}"
        )
        raise ServerError(
            f"Unable to request recipe via HTTP {response.status_code}): "
            f"{response.json}",
        )

    try:
        task_id = response.json.get("requested", []).pop()
        if not task_id:
            raise ServerError("task_id is False")
    except Exception as exc:
        raise ServerError(
            f"Couldn't retrieve requested task id: {exc}",
        ) from exc

    # remove newly created recipe (not needed anymore)
    response = query_api(
        f"{Context.zimfarm_api_url}/recipes/{recipe_name}",
        method="DELETE",
        headers=zimfarm_client_token_provider.get_authorization_header(),
    )
    if not response.success:
        logger.error(
            f"Unable to remove recipe {recipe_name} via HTTP {response.status_code}: "
            f"{response.json}"
        )
    db_requested_task.create_requested_task(
        session,
        recipe_id=UUID(recipe_id),
        task_id=UUID(task_id),
        s3_url=Context.zim_upload_s3_bucket_uri,
        s3_key=request.file.key,
        requested_by=current_account.id,
        collection_id=collection.id,
    )
    return db_requested_task.create_requested_task_schema(
        db_requested_task.get_requested_task(session, UUID(task_id))
    )
