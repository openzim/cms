from collections.abc import Callable
from uuid import uuid4

import pytest
from faker import Faker
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import count_from_stmt
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account, Book, Title, TitleFlavour, ZimfarmRecipe
from cms_backend.db.zimfarm_recipe import (
    create_zimfarm_recipe,
    get_zimfarm_recipe,
    get_zimfarm_recipe_by_id_or_none,
    get_zimfarm_recipe_history,
    get_zimfarm_recipe_history_entry_or_none,
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
    account: Account,
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
            author=account,
        )


def test_update_zimfarm_recipe_update_existing_title_flavours(
    dbsession: OrmSession,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    create_title: Callable[..., Title],
    account: Account,
):
    recipe = create_zimfarm_recipe()
    title = create_title(flavours=["maxi", "mini"], zimfarm_recipe=recipe)
    update_zimfarm_recipe(
        dbsession,
        recipe=recipe,
        flavours=["maxi", "nopic", "mini"],
        title=title,
        old_recipes={recipe.id},
        author=account,
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
    account: Account,
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
        author=account,
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
    account: Account,
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
        author=account,
    )
    dbsession.refresh(book)
    assert len(book.issues) == 0


def test_update_zimfarm_recipe_dissociate_recipes_from_flavours(
    dbsession: OrmSession,
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    create_title: Callable[..., Title],
    account: Account,
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
        author=account,
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


@pytest.mark.parametrize(
    "skip, limit, expected_count",
    [
        pytest.param(0, 3, 3, id="first-page"),
        pytest.param(3, 3, 3, id="second-page"),
        pytest.param(6, 2, 0, id="page-num-too-high-no-results"),
        pytest.param(0, 1, 1, id="first-page-with-low-limit"),
        pytest.param(0, 10, 6, id="first-page-with-high-limit"),
    ],
)
def test_get_zimfarm_recipe_history(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    account: Account,
    skip: int,
    limit: int,
    expected_count: int,
):
    """Test retrieving zimfarm recipe history with pagination"""
    title = create_title(name="wikipedia_en_test")
    recipe = create_zimfarm_recipe(title_id=title.id)
    for flavour in ["mini", "maxi", "nopic", "", "novid"]:
        update_zimfarm_recipe(
            dbsession,
            recipe=recipe,
            author=account,
            flavours=[flavour],
            title=title,
            old_recipes=set(),
            create_event=False,
        )

    results = get_zimfarm_recipe_history(
        dbsession,
        recipe_identifier=recipe.name,
        skip=skip,
        limit=limit,
    )
    assert results.nb_records == 6
    assert len(results.records) <= limit
    assert len(results.records) == expected_count


def test_get_zimfarm_recipe_history_entry_or_none(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_zimfarm_recipe: Callable[..., ZimfarmRecipe],
    account: Account,
):
    """Test retrieving a specific title history entry"""
    title = create_title(name="wikipedia_en_test")
    recipe = create_zimfarm_recipe(title_id=title.id)
    recipe = update_zimfarm_recipe(
        dbsession,
        recipe=recipe,
        author=account,
        flavours=["maxi"],
        title=title,
        old_recipes=set(),
        create_event=False,
    )
    assert len(recipe.history_entries) == 2

    history_result = get_zimfarm_recipe_history(
        dbsession, recipe_identifier=str(recipe.id), skip=1, limit=1
    )
    history_id = history_result.records[0].id

    history_entry = get_zimfarm_recipe_history_entry_or_none(
        dbsession, recipe_identifier=str(recipe.id), history_id=history_id
    )
    assert history_entry is not None
    assert history_entry.flavours == []
