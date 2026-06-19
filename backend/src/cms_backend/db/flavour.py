from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import selectinload

from cms_backend.db.models import Title, TitleFlavour
from cms_backend.schemas.orms import TitleFlavourSchema


def get_title_flavours(title: Title) -> list[str]:
    return [title_flavour.flavour for title_flavour in title.flavours]


def create_title_flavour_schema(tf: TitleFlavour) -> TitleFlavourSchema:
    return TitleFlavourSchema(flavour=tf.flavour, recipe_id=tf.recipe_id)


def get_title_flavour_or_none(
    session: OrmSession, title_id: UUID, flavour: str
) -> TitleFlavour | None:
    return session.scalars(
        select(TitleFlavour)
        .where(TitleFlavour.title_id == title_id, TitleFlavour.flavour == flavour)
        .options(selectinload(TitleFlavour.recipe))
    ).one_or_none()
