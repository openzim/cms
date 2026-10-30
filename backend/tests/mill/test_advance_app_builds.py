from collections.abc import Callable
from unittest.mock import patch

from sqlalchemy.orm import Session as OrmSession

import cms_backend.mill.advance_app_builds as mill_advance
from cms_backend.db.app_build import get_build
from cms_backend.db.models import (
    AppBuildPhase,
    Application,
    ApplicationBuild,
    Title,
)
from cms_backend.mill.advance_app_builds import advance_app_builds


def test_advance_app_builds_advances_all_in_progress(
    dbsession: OrmSession,
    create_title: Callable[..., Title],
    create_application: Callable[..., Application],
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    title = create_title(flavours=["maxi", "mini"])
    maxi_application = create_application(title=title, flavour="maxi", name="phet")
    mini_application = create_application(title=title, flavour="mini", name="phet2")
    first = create_app_build(
        application=maxi_application,
        status="running",
        phase=AppBuildPhase.CHECKS.value,
        build=0,
    )
    second = create_app_build(
        application=mini_application,
        status="pending",
        phase=AppBuildPhase.MERGE.value,
        build=1,
    )
    first_id = first.id
    second_id = second.id

    with (
        patch.object(
            mill_advance, "advance_app_build", return_value=True
        ) as mock_advance,
        patch.object(mill_advance, "fail_app_build") as mock_fail,
    ):
        advance_app_builds(dbsession)

    assert mock_advance.call_count == 2
    assert {call.args[0].id for call in mock_advance.call_args_list} == {
        first_id,
        second_id,
    }
    mock_fail.assert_not_called()


def test_advance_app_builds_fails_on_error(
    dbsession: OrmSession,
    application: Application,
    create_app_build: Callable[..., ApplicationBuild],
) -> None:
    build = create_app_build(
        application=application,
        status="running",
        phase=AppBuildPhase.CHECKS.value,
    )
    build_id = build.id

    with (
        patch.object(
            mill_advance,
            "advance_app_build",
            side_effect=ValueError("error"),
        ) as mock_advance,
        patch.object(
            mill_advance,
            "fail_app_build",
            wraps=mill_advance.fail_app_build,
        ) as mock_fail,
    ):
        advance_app_builds(dbsession)

    mock_advance.assert_called_once_with(build)
    mock_fail.assert_called_once_with(
        build,
        "Unexpected error while advancing build: error",
    )

    refreshed = get_build(dbsession, build_id=build_id)
    assert refreshed.status == "failure"
    assert refreshed.phase is None
