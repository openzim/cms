from collections.abc import Callable
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

import cms_backend.mill.process_publication_requests as mill_process
from cms_backend.db.event import (
    PUBLICATION_REQUESTED_TOPIC,
    create_publication_requested_event,
)
from cms_backend.db.models import ApplicationPublication, Event, PublicationPhase
from cms_backend.mill.process_publication_requests import (
    process_publication_requests,
)
from cms_backend.utils.datetime import getnow
from cms_backend.utils.github import PublicationPullRequestResult, github_client


def test_process_publication_requests_event_missing_keys(
    dbsession: OrmSession,
) -> None:
    event = Event(
        created_at=getnow(),
        topic=PUBLICATION_REQUESTED_TOPIC,
        payload={"unexpected": "value"},
    )
    dbsession.add(event)
    dbsession.flush()
    event_id = event.id

    process_publication_requests(dbsession)

    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )


def test_process_publication_requests_unknown_publication(
    dbsession: OrmSession,
) -> None:
    event = create_publication_requested_event(dbsession, publication_id=uuid4())
    event_id = event.id

    process_publication_requests(dbsession)

    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )


def test_process_publication_requests_starts_publication(
    dbsession: OrmSession,
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication(
        status="pending", phase=PublicationPhase.REQUESTED.value
    )
    event = create_publication_requested_event(dbsession, publication_id=publication.id)
    event_id = event.id
    publication_id = publication.id

    result = PublicationPullRequestResult(
        branch="cms/publication-test",
        base_sha="basesha",
        pr_number=12,
        pr_url="https://github.test/pr/12",
    )

    with patch.object(
        github_client,
        "create_publication_pull_request",
        return_value=result,
    ) as mock_create_pull_request:
        process_publication_requests(dbsession)

    mock_create_pull_request.assert_called_once_with(
        store="android",
        app_name="phet",
        content_version="2026-05",
        zim_filename="phet_mul_all_maxi_2026-05.zim",
        branch="cms/publication-test",
        publication_id=str(publication_id),
    )
    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )
    assert publication.phase == PublicationPhase.CHECKS.value
    assert publication.status == "running"
    assert publication.pr_number == 12
    assert publication.pr_url == "https://github.test/pr/12"


def test_process_publication_requests_fails_publication_on_error(
    dbsession: OrmSession,
    create_publication: Callable[..., ApplicationPublication],
) -> None:
    publication = create_publication()
    event = create_publication_requested_event(dbsession, publication_id=publication.id)
    event_id = event.id

    with (
        patch.object(
            mill_process,
            "start_publication",
            side_effect=ValueError("Unexpected error while starting publication"),
        ) as mock_start_publication,
        patch.object(
            mill_process,
            "fail_publication",
            wraps=mill_process.fail_publication,
        ) as mock_fail_publication,
    ):
        process_publication_requests(dbsession)

    mock_start_publication.assert_called_once_with(publication)
    mock_fail_publication.assert_called_once_with(
        publication,
        "Unexpected error while starting publication",
    )
    assert (
        dbsession.scalars(select(Event).where(Event.id == event_id)).one_or_none()
        is None
    )
    assert publication.status == "failure"
    assert publication.phase is None
    assert publication.error == "Unexpected error while starting publication"
