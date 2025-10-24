from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Title
from cms_backend.db.title import get_title_by_name_or_none


def test_get_title_by_name_or_none(
    dbsession: OrmSession,
    title: Title,  # noqa: ARG001
):
    """Create a book from a zimfarm notification"""
    assert get_title_by_name_or_none(dbsession, name="foo") is None
    test_fr_title = get_title_by_name_or_none(dbsession, name="test_en_all")
    assert test_fr_title is not None
    assert test_fr_title.name == "test_en_all"
