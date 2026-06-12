from collections.abc import Callable
from uuid import uuid4

import pytest
from faker import Faker
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Title, ZimfarmRecipe
from cms_backend.db.zimfarm_recipe import (
    create_zimfarm_recipe,
    get_zimfarm_recipe,
    get_zimfarm_recipe_by_id_or_none,
)


def test_get_zimfarm_recipe_or_none(dbsession: OrmSession):
    assert get_zimfarm_recipe_by_id_or_none(dbsession, uuid4()) is None


def test_get_zimfarm_recipe_not_found(dbsession: OrmSession):
    with pytest.raises(RecordDoesNotExistError):
        get_zimfarm_recipe(dbsession, uuid4())


def test_get_zimfarm_recipe(
    dbsession: OrmSession, create_zimfarm_recipe: Callable[..., ZimfarmRecipe]
):
    recipe = create_zimfarm_recipe(recipe_id=uuid4(), recipe_name="test_recipe")
    db_recipe = get_zimfarm_recipe(dbsession, recipe.id)
    assert db_recipe.id == recipe.id


def test_create_zimfarm_recipe(dbsession: OrmSession, title: Title, faker: Faker):
    recipe = create_zimfarm_recipe(
        dbsession, recipe_id=faker.uuid4(), recipe_name=faker.name(), title_id=title.id
    )
    assert recipe.title_id == title.id
