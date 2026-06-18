from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as OrmSession

from cms_backend.api.routes.dependencies import require_permission
from cms_backend.api.routes.models import ListResponse, calculate_pagination_metadata
from cms_backend.db import gen_dbsession
from cms_backend.db.title import get_title
from cms_backend.db.zimfarm_recipe import (
    create_zimfarm_recipe_schema,
)
from cms_backend.db.zimfarm_recipe import (
    get_zimfarm_recipe as db_get_zimfarm_recipe,
)
from cms_backend.db.zimfarm_recipe import (
    get_zimfarm_recipes as db_get_zimfarm_recipes,
)
from cms_backend.db.zimfarm_recipe import (
    update_zimfarm_recipe as db_update_zimfarm_recipe,
)
from cms_backend.schemas import BaseModel
from cms_backend.schemas.fields import LimitFieldMax200, NotEmptyString, SkipField
from cms_backend.schemas.orms import ZimfarmRecipeFullSchema, ZimfarmRecipeLightSchema

router = APIRouter(prefix="/recipes", tags=["zimfarm-recipes"])


class ZimfarmRecipesGetSchema(BaseModel):
    skip: SkipField = 0
    limit: LimitFieldMax200 = 20
    name: NotEmptyString | None = None


class RecipeUpdateSchema(BaseModel):
    title_name: NotEmptyString
    flavours: list[str]
    old_recipes: set[UUID]


@router.get("")
def get_zimfarm_recipes(
    params: Annotated[ZimfarmRecipesGetSchema, Query()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ListResponse[ZimfarmRecipeLightSchema]:
    """Get a list of zimfarm recipes"""

    results = db_get_zimfarm_recipes(
        session,
        skip=params.skip,
        limit=params.limit,
        name=params.name,
    )

    return ListResponse[ZimfarmRecipeLightSchema](
        meta=calculate_pagination_metadata(
            nb_records=results.nb_records,
            skip=params.skip,
            limit=params.limit,
            page_size=len(results.records),
        ),
        items=results.records,
    )


@router.get("/{recipe_identifier}")
def get_zimfarm_recipe(
    recipe_identifier: Annotated[NotEmptyString, Path()],
    session: Annotated[OrmSession, Depends(gen_dbsession)],
) -> ZimfarmRecipeFullSchema:
    return create_zimfarm_recipe_schema(
        db_get_zimfarm_recipe(session, recipe_identifier)
    )


@router.put(
    "/{recipe_identifier}",
    dependencies=[
        Depends(require_permission(namespace="title", name="update")),
        Depends(require_permission(namespace="recipe", name="update")),
    ],
)
def update_zimfarm_recipe(
    recipe_identifier: Annotated[NotEmptyString, Path()],
    request: RecipeUpdateSchema,
    session: OrmSession = Depends(gen_dbsession),
):
    title = get_title(session, request.title_name)
    recipe = db_get_zimfarm_recipe(session, recipe_identifier)
    db_update_zimfarm_recipe(
        session,
        recipe=recipe,
        flavours=request.flavours,
        title=title,
        old_recipes=request.old_recipes,
    )

    return JSONResponse(
        content={"message": f"recipe '{recipe_identifier}' has been updated"},
        status_code=HTTPStatus.OK,
    )
