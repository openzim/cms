from collections.abc import Callable
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

from cms_backend.db.models import Title
from cms_backend.mill.process_retention_rules import process_retention_rules


def test_process_retention_rules(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    """Test that apply_retention_rules is called for all titles"""
    title1 = create_title(name="wikipedia_en_all")
    title2 = create_title(name="wikipedia_fr_all")

    with patch(
        "cms_backend.mill.process_retention_rules.apply_retention_rules"
    ) as mock_apply:
        process_retention_rules(dbsession)

        assert mock_apply.call_count == 2
        calls = mock_apply.call_args_list
        titles_called = [call[0][1] for call in calls]
        assert title1 in titles_called
        assert title2 in titles_called


def test_process_retention_rules_continues_on_error(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
):
    """Test that an error in one title doesn't stop the processing of others"""
    create_title(name="wikipedia_en_all")
    create_title(name="wikipedia_fr_all")

    def side_effect(session: OrmSession, title: Title) -> None:  # noqa: ARG001
        if title.name == "wikipedia_en_all":
            raise Exception("Test error")

    with patch(
        "cms_backend.mill.process_retention_rules.apply_retention_rules",
        side_effect=side_effect,
    ) as mock_apply:
        process_retention_rules(dbsession)

        assert mock_apply.call_count == 2
