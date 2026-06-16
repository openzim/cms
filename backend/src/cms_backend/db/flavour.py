from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Title, TitleFlavour


def get_title_flavours(title: Title) -> list[str]:
    return [title_flavour.flavour for title_flavour in title.flavours]


def get_title_flavour_or_none(
    session: OrmSession, title_id: UUID, flavour: str
) -> TitleFlavour | None:
    return session.scalars(
        select(TitleFlavour).where(
            TitleFlavour.title_id == title_id, TitleFlavour.flavour == flavour
        )
    ).one_or_none()
