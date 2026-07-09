from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Title, TitleFlavour
from cms_backend.schemas.orms import TitleFlavourSchema


def get_title_flavours(title: Title) -> list[str]:
    return [title_flavour.flavour for title_flavour in title.flavours]


def create_title_flavour_schema(tf: TitleFlavour) -> TitleFlavourSchema:
    return TitleFlavourSchema(flavour=tf.flavour, recipe_id=tf.recipe_id)


def create_title_flavour(
    session: OrmSession, title: Title, recipe_id: UUID | None, flavour: str
):
    title_flavour = TitleFlavour(
        flavour=flavour,
        recipe_id=recipe_id,
    )
    title.flavours.append(title_flavour)
    session.add(title_flavour)
    session.flush()


def get_title_flavour_or_none(
    session: OrmSession, title_id: UUID, flavour: str
) -> TitleFlavour | None:
    return session.scalars(
        select(TitleFlavour).where(
            TitleFlavour.title_id == title_id, TitleFlavour.flavour == flavour
        )
    ).one_or_none()


def get_title_flavour(
    session: OrmSession, title_id: UUID, flavour: str
) -> TitleFlavour:
    title_flavour = get_title_flavour_or_none(session, title_id, flavour)
    if title_flavour is None:
        raise RecordDoesNotExistError(
            f"Title flavour {flavour} for title {title_id} does not exists"
        )
    return title_flavour
