from collections.abc import Callable
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

import cms_backend.mill.advance_publications as mill_advance
from cms_backend.db.models import ApplicationPublication, PublicationPhase, Title
from cms_backend.db.publication import get_publication
from cms_backend.mill.advance_publications import advance_publications


def test_advance_publications_advances_all_in_progress(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    title = create_title(flavours=["maxi", "mini"])
    first = create_publication(
        title=title,
        flavour="maxi",
        status="running",
        phase=PublicationPhase.CHECKS.value,
        build=0,
    )
    second = create_publication(
        title=title,
        flavour="mini",
        status="pending",
        phase=PublicationPhase.MERGE.value,
        build=1,
    )
    first_id = first.id
    second_id = second.id

    with (
        patch.object(
            mill_advance, "advance_publication", return_value=True
        ) as mock_advance,
        patch.object(mill_advance, "fail_publication") as mock_fail,
    ):
        advance_publications(dbsession)

    assert mock_advance.call_count == 2
    assert {call.args[0].id for call in mock_advance.call_args_list} == {
        first_id,
        second_id,
    }
    mock_fail.assert_not_called()


def test_advance_publications_fails_on_error(
    dbsession: OrmSession,
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="running", phase=PublicationPhase.CHECKS.value
    )
    publication_id = publication.id

    with (
        patch.object(
            mill_advance,
            "advance_publication",
            side_effect=ValueError("error"),
        ) as mock_advance,
        patch.object(
            mill_advance,
            "fail_publication",
            wraps=mill_advance.fail_publication,
        ) as mock_fail,
    ):
        advance_publications(dbsession)

    mock_advance.assert_called_once_with(publication)
    mock_fail.assert_called_once_with(
        publication,
        "Unexpected error while advancing publication: error",
    )

    refreshed = get_publication(dbsession, publication_id=publication_id)
    assert refreshed.status == "failure"
    assert refreshed.phase is None
