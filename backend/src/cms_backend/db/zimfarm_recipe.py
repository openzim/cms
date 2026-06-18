from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from cms_backend.db import count_from_stmt
from cms_backend.db.event import create_title_modified_event
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.flavour import get_title_flavour_or_none
from cms_backend.db.models import Book, Title, TitleFlavour, ZimfarmRecipe
from cms_backend.db.title import get_title_by_id
from cms_backend.schemas.orms import (
    ListResult,
    TitleFlavourSchema,
    ZimfarmRecipeFullSchema,
    ZimfarmRecipeLightSchema,
)
from cms_backend.utils import is_valid_uuid


def get_zimfarm_recipe_by_id_or_none(
    session: OrmSession, recipe_id: UUID
) -> ZimfarmRecipe | None:
    """Get a zimfarm recipe by ID if possible else None"""
    return session.scalars(
        select(ZimfarmRecipe)
        .where(ZimfarmRecipe.id == recipe_id)
        .options(selectinload(ZimfarmRecipe.title))
    ).one_or_none()


def get_zimfarm_recipe_by_name_or_none(
    session: OrmSession, recipe_name: str
) -> ZimfarmRecipe | None:
    """Get a zimfarm recipe by ID if possible else None"""
    return session.scalars(
        select(ZimfarmRecipe)
        .where(ZimfarmRecipe.name == recipe_name)
        .options(
            selectinload(ZimfarmRecipe.title), selectinload(ZimfarmRecipe.flavours)
        )
    ).one_or_none()


def get_zimfarm_recipe(session: OrmSession, recipe_identifier: str):
    """Get a zimfarm recipe by ID/name if possible else raise an exception"""
    if is_valid_uuid(recipe_identifier):
        zimfarm_recipe = get_zimfarm_recipe_by_id_or_none(
            session, UUID(recipe_identifier)
        )
    else:
        zimfarm_recipe = get_zimfarm_recipe_by_name_or_none(session, recipe_identifier)

    if zimfarm_recipe is None:
        raise RecordDoesNotExistError(
            f"Zimfarm recipe {recipe_identifier} does not exist"
        )
    return zimfarm_recipe


def create_zimfarm_recipe_schema(
    zimfarm_recipe: ZimfarmRecipe,
) -> ZimfarmRecipeFullSchema:
    return ZimfarmRecipeFullSchema(
        id=zimfarm_recipe.id,
        name=zimfarm_recipe.name,
        flavours=[
            TitleFlavourSchema(flavour=tf.flavour, recipe_id=tf.recipe_id)
            for tf in zimfarm_recipe.flavours
        ],
        title_id=zimfarm_recipe.title.id if zimfarm_recipe.title else None,
        title_name=zimfarm_recipe.title.name if zimfarm_recipe.title else None,
    )


def create_zimfarm_recipe(
    session: OrmSession,
    *,
    recipe_id: str,
    recipe_name: str,
    title_id: UUID | None | None = None,
) -> ZimfarmRecipe:
    """Create a zimfarm recipe in the DB."""
    zimfarm_recipe = ZimfarmRecipe(
        id=UUID(recipe_id),
        name=recipe_name,
    )
    if title_id is not None:
        title = get_title_by_id(session, title_id=title_id)
        zimfarm_recipe.title = title
    session.add(zimfarm_recipe)
    session.flush()
    return zimfarm_recipe


def update_zimfarm_recipe(
    session: OrmSession,
    *,
    recipe: ZimfarmRecipe,
    flavours: list[str],
    title: Title,
    old_recipes: set[UUID],
    create_event: bool = True,
):
    """Update a recipe to be associated with the title and flavours.

    - Existing associations with the title's flavours to other recipes
        are removed. These other recipe(s) must be in the list of old recipes.
    - Old title flavours belonging to the title are deleted and new ones are created
        and attached to recipe.
    - Books with a matching title name have recipe issues removed
    """

    associated_recipes: set[UUID] = set()

    for flavour in flavours:
        title_flavour = get_title_flavour_or_none(session, title.id, flavour)
        if title_flavour:
            associated_recipes.add(title_flavour.recipe_id)

            if title_flavour.recipe_id != recipe.id:
                title_flavour.recipe = recipe
        else:
            title_flavour = TitleFlavour(flavour=flavour)
            title_flavour.recipe = recipe
            title_flavour.title = title
            session.add(title_flavour)

    if associated_recipes != old_recipes:
        raise ValueError("Mismatch between old recipes and title flavour recipes ")

    # Clear title id from recipes with no remaining flavours
    recipes_with_flavours: set[UUID] = set(
        session.scalars(
            select(TitleFlavour.recipe_id).where(TitleFlavour.title_id == title.id)
        )
    )
    all_title_recipes: set[UUID] = {recipe.id for recipe in title.zimfarm_recipes}
    recipes_to_clear = all_title_recipes - recipes_with_flavours
    if recipes_to_clear:
        session.execute(
            update(ZimfarmRecipe)
            .where(ZimfarmRecipe.id.in_(recipes_to_clear))
            .values({"title_id": None})
        )

    recipe.title = title

    session.flush()

    if create_event:
        # Optimistically remove recipe issues from books that will be processed by the
        # event
        books = session.scalars(
            select(Book).where(
                Book.title_id.is_(None),
                Book.has_error.is_(False),
                Book.name == title.name,
                Book.location_kind.not_in(["deleted", "to_delete"]),
                Book.issues.contains(["recipe issue"]),
            )
        ).all()
        for book in books:
            book.issues.remove("recipe issue")
            flag_modified(book, "issues")

        create_title_modified_event(
            session, action="updated", title_name=title.name, title_id=title.id
        )


def get_zimfarm_recipes(
    session: OrmSession,
    *,
    skip: int,
    limit: int,
    name: str | None = None,
) -> ListResult[ZimfarmRecipeLightSchema]:
    """Get a list of recipes"""

    stmt = select(
        ZimfarmRecipe.id.label("recipe_id"), ZimfarmRecipe.name.label("recipe_name")
    ).where(
        (
            ZimfarmRecipe.name.ilike(f"%{name if name is not None else ''}%")
            | (name is None)
        ),
    )

    return ListResult[ZimfarmRecipeLightSchema](
        nb_records=count_from_stmt(session, stmt),
        records=[
            ZimfarmRecipeLightSchema(
                id=recipe_id,
                name=recipe_name,
            )
            for recipe_id, recipe_name in session.execute(
                stmt.offset(skip).limit(limit)
            ).all()
        ],
    )
