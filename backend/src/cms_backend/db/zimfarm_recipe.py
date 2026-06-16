from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db.event import create_title_modified_event
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.flavour import get_title_flavours
from cms_backend.db.models import Title, TitleFlavour, ZimfarmRecipe


def get_zimfarm_recipe_by_id_or_none(
    session: OrmSession, recipe_id: UUID
) -> ZimfarmRecipe | None:
    """Get a zimfarm recipe by ID if possible else None"""
    return session.scalars(
        select(ZimfarmRecipe)
        .where(ZimfarmRecipe.id == recipe_id)
        .options(selectinload(ZimfarmRecipe.title))
    ).one_or_none()


def get_zimfarm_recipe(session: OrmSession, recipe_id: UUID):
    """Get a zimfarm recipe by ID if possible else raise an exception"""
    if (zimfarm_recipe := get_zimfarm_recipe_by_id_or_none(session, recipe_id)) is None:
        raise RecordDoesNotExistError(
            f"Zimfarm recipe with ID {recipe_id} does not exist"
        )
    return zimfarm_recipe


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
    zimfarm_recipe.title_id = title_id
    session.add(zimfarm_recipe)
    session.flush()
    return zimfarm_recipe


def update_zimfarm_recipe(
    session: OrmSession,
    *,
    recipe: ZimfarmRecipe,
    flavours: list[str],
    title: Title,
    current_recipes: set[UUID],
):
    """Update a recipe to be associated with the title and flavours.

    - Existing associations with the title and it's flavours to other recipes
        are removed. These other recipe(s) must be in the list of current recipes.
    - Old title flavours belonging to the title are deleted and new ones are created.
    """
    associated_recipes: set[UUID] = set()
    for zimfarm_recipe in title.zimfarm_recipes:
        associated_recipes.add(zimfarm_recipe.id)

    for title_flavour in title.flavours:
        if title_flavour.recipe_id:
            associated_recipes.add(title_flavour.recipe_id)

    if associated_recipes != current_recipes:
        raise ValueError(
            "Mismatch between current recipes and title/title flavour recipes"
        )

    existing_flaovurs = get_title_flavours(title)
    if set(existing_flaovurs) != set(flavours):
        for title_flavour in list(title.flavours):
            session.delete(title_flavour)

        title.flavours.clear()
        session.flush()

        for flavour in flavours:
            title_flavour = TitleFlavour(flavour=flavour)
            title_flavour.recipe = recipe
            title_flavour.title = title
            session.add(title_flavour)

    recipe.title = title

    for zimfarm_recipe in title.zimfarm_recipes:
        if zimfarm_recipe.title_id != recipe.title_id:
            zimfarm_recipe.title = None
            session.add(zimfarm_recipe)

    session.flush()
    create_title_modified_event(
        session, action="updated", title_name=title.name, title_id=title.id
    )
