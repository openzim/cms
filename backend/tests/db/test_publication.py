from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session as OrmSession

from cms_backend.db import publication as db_publication
from cms_backend.db.exceptions import RecordDoesNotExistError
from cms_backend.db.models import Account, ApplicationPublication, Title
from cms_backend.schemas.models import ApplicationPublicationCreateSchema
from cms_backend.utils.github import github_client


def test_create_publication(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    account: Account,
) -> None:
    title = create_title(flavours=["maxi"])

    publication = db_publication.create_publication(
        dbsession,
        payload=ApplicationPublicationCreateSchema(
            title_id=title.id,
            flavour="maxi",
            store="android",
            content_version="2026-05",
            tag="phet_2026.05.0",
            commit_sha="abc",
            repository="kiwix/kiwix-android-branded",
            workflow="cd.yml",
            release_id=1,
            release_url="https://github.test/release/1",
            requested_by_id=account.id,
        ),
    )

    assert publication.status == "pending"
    assert publication.tag == "phet_2026.05.0"
    assert publication.requested_by_id == account.id


def test_get_publication(
    dbsession: OrmSession,
    publication: ApplicationPublication,
) -> None:
    result = db_publication.get_publication(dbsession, publication_id=publication.id)

    assert result.id == publication.id
    assert result.title_id == publication.title_id
    assert result.flavour == publication.flavour
    assert result.store == publication.store


def test_get_publication_not_found(
    dbsession: OrmSession,
) -> None:
    with pytest.raises(RecordDoesNotExistError):
        db_publication.get_publication(dbsession, publication_id=uuid4())


@pytest.mark.parametrize(
    ("title_name", "flavour", "store", "expected_count"),
    [
        pytest.param(None, None, None, 3, id="no-filters"),
        pytest.param("phet_mul_all", None, None, 2, id="title"),
        pytest.param("wikipedia_en_all", None, None, 1, id="title-single"),
        pytest.param("phet_mul_all", "mini", None, 1, id="title-and-flavour"),
        pytest.param(None, None, "android", 2, id="store"),
        pytest.param(None, "maxi", None, 2, id="flavour"),
        pytest.param("phet_mul_all", "maxi", "android", 1, id="all-filters"),
        pytest.param("wikipedia_en_all", "maxi", "android", 0, id="no-match"),
    ],
)
def test_get_publications_filters(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_publication: Callable[..., ApplicationPublication],
    title_name: str | None,
    flavour: str | None,
    store: str | None,
    expected_count: int,
) -> None:
    phet_title = create_title(name="phet_mul_all", flavours=["maxi", "mini"])
    wikipedia_title = create_title(name="wikipedia_en_all", flavours=["maxi"])
    create_publication(
        title=phet_title, flavour="maxi", store="android", app_name="phet", build=0
    )
    create_publication(
        title=phet_title, flavour="mini", store="android", app_name="phet", build=1
    )
    create_publication(
        title=wikipedia_title,
        flavour="maxi",
        store="apple",
        app_name="wikipedia",
    )

    title_id = {
        "phet_mul_all": phet_title.id,
        "wikipedia_en_all": wikipedia_title.id,
    }.get(title_name or "")

    result = db_publication.get_publications(
        dbsession,
        title_id=title_id,
        flavour=flavour,
        store=store,
    )

    assert result.nb_records == expected_count
    assert len(result.records) == expected_count


@pytest.mark.parametrize(
    ("status", "tag", "app_name", "content_version", "expected"),
    [
        ("success", "phet_2026.05.0", "phet", "2026-05", True),
        ("success", "phet_2026.05.2", "phet", "2026-05", True),
        ("success", "phet_2026.05.2", "phet2", "2026-05", False),
        ("success", "phet_2026.05.2", "phet", "2026-06", False),
        ("failure", "phet_2026.05.0", "phet", "2026-05", False),
    ],
)
def test_has_successful_publication(
    dbsession: OrmSession,
    publication: ApplicationPublication,
    *,
    status: str,
    tag: str,
    app_name: str,
    content_version: str,
    expected: bool,
) -> None:
    publication.status = status
    publication.tag = tag

    assert (
        db_publication.has_successful_publication(
            dbsession,
            title_id=publication.title_id,
            flavour=publication.flavour,
            store=publication.store,
            app_name=app_name,
            content_version=content_version,
        )
        is expected
    )


def test_refresh_publication_success(
    dbsession: OrmSession,
    publication: ApplicationPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_run(**_kwargs: Any) -> dict[str, Any]:
        return {
            "id": 7,
            "html_url": "https://github.test/run/7",
            "status": "completed",
            "conclusion": "success",
        }

    monkeypatch.setattr(github_client, "get_run_for_publication", fake_get_run)

    refreshed = db_publication.refresh_publication(dbsession, publication)

    assert refreshed.status == "success"
    assert refreshed.run_id == 7
    assert refreshed.run_url == "https://github.test/run/7"


def test_refresh_publication_failure(
    dbsession: OrmSession,
    publication: ApplicationPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_run(**_kwargs: Any) -> dict[str, Any]:
        return {
            "id": 8,
            "html_url": "https://github.test/run/8",
            "status": "completed",
            "conclusion": "failure",
        }

    monkeypatch.setattr(github_client, "get_run_for_publication", fake_get_run)

    refreshed = db_publication.refresh_publication(dbsession, publication)

    assert refreshed.status == "failure"
    assert refreshed.error == "failure"
