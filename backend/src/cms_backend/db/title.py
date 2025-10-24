from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Title


def get_title_by_name_or_none(session: OrmSession, *, name: str) -> Title | None:
    """Get a title by name if possible else None"""

    return session.scalars(select(Title).where(Title.name == name)).one_or_none()
