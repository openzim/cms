from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID, uuid4

from botocore.exceptions import (  # pyright: ignore[reportMissingTypeStubs]
    ClientError as S3ClientError,
)
from fastapi import APIRouter, Depends, Path, Query, Response
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.orm import Session as OrmSession

from cms_backend import logger
from cms_backend.api.context import Context as ApiContext
from cms_backend.api.routes.dependencies import (
    get_accessible_collection_ids,
    get_current_account,
    get_current_account_or_none,
    require_permission,
)
from cms_backend.api.routes.http_errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    ServerError,
)
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.api.token import zimfarm_client_token_provider
from cms_backend.context import Context
from cms_backend.db import account as db_account
from cms_backend.db import flavour as db_flavour
from cms_backend.db import gen_dbsession
from cms_backend.db import title as db_title
from cms_backend.db import title_upload as db_title_upload
from cms_backend.db.models import Account
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import (
    LimitFieldMax200,
    NotEmptyString,
    SkipField,
    ZimFlavour,
)
from cms_backend.schemas.models import (
    PartEtag,
    RestoreTitlesSchema,
    S3MultipartUpload,
    TitleCreateSchema,
    TitleUpdateSchema,
)
from cms_backend.schemas.orms import (
    TitleFlavourSchema,
    TitleFullSchema,
    TitleHistorySchema,
    TitleLightSchema,
    TitleUploadLightSchema,
)
from cms_backend.utils import is_valid_uuid
from cms_backend.utils.requests import query_api
from cms_backend.utils.s3 import (
    complete_multipart_upload,
    generate_multipart_upload_presigned_urls,
    generate_view_presigned_url,
    get_kiwix_storage_client,
)

router = APIRouter(prefix="/titles", tags=["titles"])


class TitlesGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None
    collection_name: NotEmptyString | None = None
    archived: bool = False
    is_rotten: bool | None = None


class RevertTitleSchema(BaseModel):
    comment: NotEmptyString | None = None


class MergeTitlesSchema(BaseModel):
    target: NotEmptyString
    sources: list[NotEmptyString]


@router.get("")
def get_titles(
    params: Annotated[TitlesGetSchema, Query()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account | None = Depends(get_current_account_or_none),
) -> ListResponse[TitleLightSchema]:
    if params.archived and not (
        current_account
        and db_account.check_account_permission(
            current_account, namespace="title", name="archive"
        )
    ):
        raise ForbiddenError("You are not allowed to view archived titles.")
    results = db_title.get_titles(
        session,
        accessible_collection_ids=accessible_collection_ids,
        skip=params.skip,
        limit=params.limit,
        name=params.name,
        collection_name=params.collection_name,
        archived=params.archived,
        is_rotten=params.is_rotten,
    )
    return ListResponse[TitleLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.post(
    "/merge",
    dependencies=[
        Depends(require_permission(namespace="title", name="update")),
        Depends(require_permission(namespace="title", name="delete")),
    ],
)
def merge_titles(
    request: MergeTitlesSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
) -> JSONResponse:
    db_title.merge_titles(
        session,
        request.target,
        request.sources,
        accessible_collection_ids=accessible_collection_ids,
    )
    return JSONResponse(
        content={"message": f"Titles have been merged with {request.target}"},
        status_code=HTTPStatus.OK,
    )


@router.get("/{title_identifier}")
def get_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
) -> TitleFullSchema:
    """Get a title by ID with full details including books"""
    if is_valid_uuid(title_identifier):
        title = db_title.get_title_by_id(
            session,
            title_id=UUID(title_identifier),
            accessible_collection_ids=accessible_collection_ids,
        )
    else:
        title = db_title.get_title_by_name(
            session,
            name=title_identifier,
            accessible_collection_ids=accessible_collection_ids,
        )
    return db_title.create_title_full_schema(title)


@router.post(
    "", dependencies=[Depends(require_permission(namespace="title", name="create"))]
)
def create_title(
    title_data: TitleCreateSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Create a new title"""
    title = db_title.create_title(
        session,
        author_id=current_account.id,
        payload=title_data,
        accessible_collection_ids=accessible_collection_ids,
    )
    return db_title.create_title_light_schema(title)


@router.patch(
    "/{title_identifier}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def update_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    title_data: TitleUpdateSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Update a title"""
    title = db_title.update_title(
        session,
        title_identifier=title_identifier,
        author_id=current_account.id,
        payload=title_data,
        accessible_collection_ids=accessible_collection_ids,
    )
    return db_title.create_title_light_schema(title)


@router.post(
    "/archive",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def archive_titles(
    request: RestoreTitlesSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> Response:
    db_title.archive_titles(
        session,
        title_names=request.title_names,
        author_id=current_account.id,
        accessible_collection_ids=accessible_collection_ids,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.post(
    "/restore",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def restore_archived_titles(
    request: RestoreTitlesSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> Response:
    db_title.restore_titles(
        session,
        title_names=request.title_names,
        author_id=current_account.id,
        accessible_collection_ids=accessible_collection_ids,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.patch(
    "/{title_identifier}/archive",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def archive_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Mark a title as archived"""
    title = db_title.archive_title(
        session,
        title_identifier=title_identifier,
        author_id=current_account.id,
        accessible_collection_ids=accessible_collection_ids,
    )
    return db_title.create_title_light_schema(title)


@router.patch(
    "/{title_identifier}/restore",
    dependencies=[Depends(require_permission(namespace="title", name="archive"))],
)
def restore_archived_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> TitleLightSchema:
    """Restore an archived title"""
    title = db_title.restore_title(
        session,
        title_identifier=title_identifier,
        author_id=current_account.id,
        accessible_collection_ids=accessible_collection_ids,
    )
    return db_title.create_title_light_schema(title)


@router.get(
    "/{title_identifier}/history",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def get_title_history(
    title_identifier: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[TitleHistorySchema]:
    results = db_title.get_title_history(
        session,
        title_identifier=title_identifier,
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
    "/{title_identifier}/flavours",
)
def get_title_flavours(
    title_identifier: Annotated[NotEmptyString, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    skip: Annotated[SkipField, Query()] = 0,
    limit: Annotated[LimitFieldMax200, Query()] = 200,
) -> ListResponse[TitleFlavourSchema]:
    title = db_title.get_title(
        session,
        title_identifier=title_identifier,
        accessible_collection_ids=accessible_collection_ids,
    )
    results = db_flavour.get_title_flavours(
        session,
        title_id=title.id,
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


class FileUploadRequest(BaseModel):
    filename: NotEmptyString
    filesize: int = Field(ge=0)
    part_size: int = Field(ge=0)
    upload_id: str | None = None


@router.post(
    "/{title_identifier}/upload/create-or-resume",
    dependencies=[
        Depends(require_permission(namespace="book", name="create")),
    ],
)
def generate_s3_presigned_urls(
    title_identifier: Annotated[NotEmptyString, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    payload: FileUploadRequest,
) -> S3MultipartUpload:
    """Generate presigned URLs for upload to S3 bucket"""
    title = db_title.get_title(
        session,
        title_identifier=title_identifier,
        accessible_collection_ids=accessible_collection_ids,
    )
    s3 = get_kiwix_storage_client(Context.zim_upload_s3_bucket_uri)
    return generate_multipart_upload_presigned_urls(
        s3,
        key=f"cms_zim_uploads/{title.name}/{uuid4()!s}.zim",
        upload_id=payload.upload_id,
        filesize=payload.filesize,
        part_size=payload.part_size,
    )


class MultipartCompleteRequest(BaseModel):
    upload_id: str
    key: str
    parts: list[PartEtag]


def _get_zimwright_recipe_create_payload(
    recipe_name: str, download_url: str
) -> dict[str, Any]:
    flags: dict[str, Any] = {"download-from": download_url}
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
    return payload


def _get_zimwright_recipe_update_payload(
    recipe_name: str, download_url: str
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": recipe_name,
        "language": "eng",
        "category": "other",
        "periodicity": "manually",
        "tags": [],
        "enabled": True,
        "offliner": "zimwright",
        "flags": {"download-from": download_url},
        "version": ApiContext.zimwright_definition_version,
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
        "warehouse_path": "/other",
    }
    return payload


def create_or_update_zimwright_recipe(
    recipe_name: str, download_url: str
) -> dict[str, Any]:
    """Create a zimwright recipe on zimfarm or update the existing one"""

    response = query_api(
        method="GET",
        url=f"{Context.zimfarm_api_url}/recipes/{recipe_name}",
        headers=zimfarm_client_token_provider.get_authorization_header(),
    )
    if response.status_code == HTTPStatus.NOT_FOUND:
        response = query_api(
            f"{Context.zimfarm_api_url}/recipes",
            method="POST",
            payload=_get_zimwright_recipe_create_payload(recipe_name, download_url),
            headers=zimfarm_client_token_provider.get_authorization_header(),
        )
        if response.success:
            recipe_id = response.json["id"]
            response = query_api(
                method="GET",
                url=f"{Context.zimfarm_api_url}/recipes/{recipe_id}",
                headers=zimfarm_client_token_provider.get_authorization_header(),
            )
    elif response.status_code == HTTPStatus.OK:
        recipe = response.json
        response = query_api(
            f"{Context.zimfarm_api_url}/recipes/{recipe['id']}",
            method="PATCH",
            payload=_get_zimwright_recipe_update_payload(recipe_name, download_url),
            headers=zimfarm_client_token_provider.get_authorization_header(),
        )
    else:
        raise ValueError(f"Unable to retrieve recipe from zimfarm: {response.json}")

    if not response.success:
        logger.error(f"Unable to create recipe: {response.json}")
        message = f"Unable to create recipe: {response.json}"
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
    return response.json


@router.post(
    "/{title_identifier}/upload/complete",
    dependencies=[
        Depends(require_permission(namespace="book", name="create")),
    ],
)
def compelete_zim_upload(
    title_identifier: Annotated[str, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
    current_account: Annotated[Account, Depends(get_current_account)],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    request: MultipartCompleteRequest,
) -> TitleUploadLightSchema:
    """Complete ZIM upload and create task on zimfarm to process ZIM file"""
    title = db_title.get_title(
        session,
        title_identifier=title_identifier,
        accessible_collection_ids=accessible_collection_ids,
    )
    s3 = get_kiwix_storage_client(Context.zim_upload_s3_bucket_uri)
    try:
        complete_multipart_upload(
            s3,
            key=request.key,
            upload_id=request.upload_id,
            parts=request.parts,
        )
    except S3ClientError as exc:  # pyright: ignore[reportUnknownVariableType]
        if exc.response["Error"]["Code"] == "NoSuchUpload":
            raise ConflictError(exc.response["Error"]["Message"]) from exc
        raise exc

    recipe = create_or_update_zimwright_recipe(
        f"zimwright_{title.name}", generate_view_presigned_url(s3, request.key)
    )

    # request a task for that newly created recipe
    response = query_api(
        f"{Context.zimfarm_api_url}/requested-tasks",
        method="POST",
        payload={
            "recipe_names": [recipe["name"]],
            "worker": ApiContext.zimtask_worker,
        },
        headers=zimfarm_client_token_provider.get_authorization_header(),
    )
    if not response.success:
        logger.error(
            f"Unable to request {recipe['name']} via HTTP {response.status_code}: "
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

    db_title_upload.create_title_upload(
        session,
        recipe_id=UUID(recipe["id"]),
        task_id=UUID(task_id),
        title_id=title.id,
        s3_key=request.key,
        requested_by=current_account.id,
    )
    return db_title_upload.create_title_upload_schema(
        db_title_upload.get_title_upload(session, UUID(task_id))
    )


@router.delete(
    "/{title_identifier}/flavours/{flavour}",
    dependencies=[
        Depends(require_permission(namespace="title", name="update")),
        Depends(require_permission(namespace="book", name="delete")),
    ],
)
def delete_title_flavour(
    title_identifier: Annotated[NotEmptyString, Path()],
    flavour: Annotated[ZimFlavour, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
) -> JSONResponse:
    title = db_title.get_title(
        session,
        title_identifier=title_identifier,
        accessible_collection_ids=accessible_collection_ids,
    )
    db_flavour.delete_title_flavour(
        session,
        title_id=title.id,
        flavour=flavour,
        accessible_collection_ids=accessible_collection_ids,
    )
    return JSONResponse(
        content={
            "message": (
                f"title flavour '{flavour}' for title '{title.name}' has been deleted"
            )
        },
        status_code=HTTPStatus.OK,
    )


@router.get(
    "/{title_identifier}/history/{history_id}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def get_title_history_entry(
    title_identifier: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
) -> TitleHistorySchema:
    history_entry = db_title.get_title_history_entry(
        session,
        title_identifier=title_identifier,
        history_id=history_id,
        accessible_collection_ids=accessible_collection_ids,
    )
    return db_title.create_title_history_schema(history_entry)


@router.patch(
    "/{title_identifier}/revert/{history_id}",
    dependencies=[Depends(require_permission(namespace="title", name="update"))],
)
def revert_title(
    title_identifier: Annotated[NotEmptyString, Path()],
    history_id: Annotated[UUID, Path()],
    request: RevertTitleSchema,
    accessible_collection_ids: Annotated[
        Sequence[UUID] | None, Depends(get_accessible_collection_ids)
    ],
    session: OrmSession = Depends(gen_dbsession),
    current_account: Account = Depends(get_current_account),
) -> JSONResponse:
    """Revert a title to a previous history."""
    db_title.revert_title(
        session,
        title_identifier=title_identifier,
        history_id=history_id,
        author_id=current_account.id,
        comment=request.comment,
        accessible_collection_ids=accessible_collection_ids,
    )
    return JSONResponse(
        content={"message": f"title '{title_identifier}' has been restored"},
        status_code=HTTPStatus.OK,
    )
