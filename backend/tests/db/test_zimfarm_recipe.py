from collections.abc import Callable
from uuid import uuid4

import pytest
from faker import Faker
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Book, Title, TitleFlavour, ZimfarmRecipe
from cms_backend.db.zimfarm_recipe import (
    create_zimfarm_recipe,
    get_zimfarm_recipe,
    get_zimfarm_recipe_by_id_or_none,
    update_zimfarm_recipe,
)


def test_get_zimfarm_recipe_or_none(dbsession: OrmSession):
    assert get_zimfarm_recipe_by_id_or_none(dbsession, uuid4()) is None


def test_get_zimfarm_recipe_not_found(dbsession: OrmSession):
    with pytest.raises(RecordDoesNotExistError):
        get_zimfarm_recipe(dbsession, str(uuid4()))


def test_get_zimfarm_recipe(
    dbsession: OrmSession, create_zimfarm_recipe: Callable[..., ZimfarmRecipe]
):
    recipe = create_zimfarm_recipe(recipe_id=uuid4(), recipe_name="test_recipe")
    db_recipe = get_zimfarm_recipe(dbsession, str(recipe.id))
    assert db_recipe.id == recipe.id


def test_create_zimfarm_recipe(dbsession: OrmSession, title: Title, faker: Faker):
    recipe = create_zimfarm_recipe(
        dbsession, recipe_id=faker.uuid4(), recipe_name=faker.name(), title_id=title.id
    )
    assert recipe.title is not None
    assert recipe.title.id == title.id


def test_update_zimfarm_recipe_mismatch_in_recipes(
    dbsession: OrmSession,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    create_title: Callable[..., Title],
):
    recipe = create_zimfarm_recipe()
    title = create_title(flavours=["maxi", "mini"], zimfarm_recipe=recipe)
    with pytest.raises(ValueError):
        update_zimfarm_recipe(
            dbsession,
            recipe=recipe,
            flavours=["nopic"],
            title=title,
            old_recipes={uuid4()},
        )


def test_update_zimfarm_recipe_update_existing_title_flavours(
    dbsession: OrmSession,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    create_title: Callable[..., Title],
):
    recipe = create_zimfarm_recipe()
    title = create_title(flavours=["maxi", "mini"], zimfarm_recipe=recipe)
    update_zimfarm_recipe(
        dbsession,
        recipe=recipe,
        flavours=["maxi", "nopic", "mini"],
        title=title,
        old_recipes={recipe.id},
    )

    assert (
        count_from_stmt(
            dbsession,
            select(TitleFlavour).where(
                TitleFlavour.title_id == title.id, TitleFlavour.recipe_id == recipe.id
            ),
        )
        == 3
    )


def test_update_zimfarm_recipe_dissociate_recipes_from_flavours_and_title_associations(
    dbsession: OrmSession,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    create_title: Callable[..., Title],
):
    recipe1 = create_zimfarm_recipe()
    title = create_title(zimfarm_recipe=recipe1)
    # "mini" and "maxi" flavours belong to recipe1
    mini = TitleFlavour(flavour="mini")
    mini.title = title
    mini.recipe = recipe1

    maxi = TitleFlavour(flavour="maxi")
    maxi.title = title
    maxi.recipe = recipe1

    dbsession.add_all([maxi, mini])

    # 'nopic' belongs to recipe2
    recipe2 = create_zimfarm_recipe()
    nopic = TitleFlavour(flavour="nopic")
    nopic.title = title
    nopic.recipe = recipe2
    dbsession.add(nopic)
    dbsession.flush()

    update_zimfarm_recipe(
        dbsession,
        recipe=recipe2,
        flavours=["maxi", "nopic", "mini"],
        title=title,
        old_recipes={recipe1.id, recipe2.id},
    )

    # all three flavours now belong to recipe2
    assert (
        count_from_stmt(
            dbsession,
            select(TitleFlavour).where(TitleFlavour.recipe_id == recipe1.id),
        )
        == 0
    )
    assert (
        count_from_stmt(
            dbsession,
            select(TitleFlavour).where(TitleFlavour.recipe_id == recipe2.id),
        )
        == 3
    )

    dbsession.refresh(recipe1)
    # recipe1 is dissociated from title because it has no flavour tied to the title
    assert recipe1.title is None
    dbsession.refresh(recipe2)
    assert recipe2.title is not None
    assert recipe2.title.id == title.id


def test_update_zimfarm_recipe_remove_book_recipe_issues(
    dbsession: OrmSession,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    create_title: Callable[..., Title],
    create_book: Callable[..., Book],
):
    recipe = create_zimfarm_recipe()
    title = create_title(flavours=["maxi", "mini"], zimfarm_recipe=recipe)
    book = create_book(name=title.name)
    book.issues = ["recipe issue"]
    dbsession.add(book)
    dbsession.flush()
    update_zimfarm_recipe(
        dbsession,
        recipe=recipe,
        flavours=["maxi", "nopic", "mini"],
        title=title,
        old_recipes={recipe.id},
    )
    dbsession.refresh(book)
    assert len(book.issues) == 0


def test_update_zimfarm_recipe_dissociate_recipes_from_flavours(
    dbsession: OrmSession,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    create_title: Callable[..., Title],
):
    recipe1 = create_zimfarm_recipe()
    title = create_title(zimfarm_recipe=recipe1)
    # "mini", "maxi" and "nopic" flavours belong to recipe1
    mini = TitleFlavour(flavour="mini")
    mini.title = title
    mini.recipe = recipe1

    maxi = TitleFlavour(flavour="maxi")
    maxi.title = title
    maxi.recipe = recipe1

    nopic = TitleFlavour(flavour="nopic")
    nopic.title = title
    nopic.recipe = recipe1

    dbsession.add_all([maxi, mini, nopic])

    # recipe2 just arrives (with mini now produced by it)
    recipe2 = create_zimfarm_recipe()
    dbsession.flush()

    update_zimfarm_recipe(
        dbsession,
        recipe=recipe2,
        flavours=["mini"],
        title=title,
        old_recipes={recipe1.id},
    )

    # recipe1 still has maxi and nopic
    assert (
        count_from_stmt(
            dbsession,
            select(TitleFlavour).where(TitleFlavour.recipe_id == recipe1.id),
        )
        == 2
    )

    # recipe 2 has mini
    assert (
        count_from_stmt(
            dbsession,
            select(TitleFlavour).where(TitleFlavour.recipe_id == recipe2.id),
        )
        == 1
    )

    dbsession.refresh(recipe1)
    assert recipe1.title is not None
    assert recipe1.title.id is title.id
    dbsession.refresh(recipe2)
    assert recipe2.title is not None
    assert recipe2.title.id == title.id
