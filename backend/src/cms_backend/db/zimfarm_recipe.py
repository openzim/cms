from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import ZimfarmRecipe


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
