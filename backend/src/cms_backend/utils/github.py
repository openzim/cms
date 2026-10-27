import re
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from cms_backend import logger
from cms_backend.api.context import Context as ApiContext
from cms_backend.utils.requests import query_api

CONTENT_VERSION_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})(?P<suffix>[a-z]*)$"
)


@dataclass(frozen=True)
class PublicationRepository:
    """GitHub repository and workflow used to publish to a given store."""

    repo: str
    workflow: str
    branch: str


@dataclass
class PublicationResult:
    tag: str
    commit_sha: str
    release_id: int
    release_url: str
    repository: str
    workflow: str


def get_tag_prefix(*, app_name: str, content_version: str) -> str:
    """Return the tag prefix, without the build number.

    Tags follow the ``<app>_<YYYY>.<MM>[suffix].<build>`` convention for every
    store. The build number starts at 0 and is incremented on every attempt.
    """
    match = CONTENT_VERSION_PATTERN.fullmatch(content_version)
    if match is None:
        raise ValueError(f"Invalid content version '{content_version}'")
    return (
        f"{app_name}_{match.group('year')}.{match.group('month')}"
        f"{match.group('suffix')}"
    )


def get_repository_config(store: str) -> PublicationRepository:
    """Get the configured repository for a publication store."""
    if store == "android":
        config = PublicationRepository(
            repo=ApiContext.github_android_repo,
            workflow=ApiContext.github_android_workflow,
            branch=ApiContext.github_android_branch,
        )
    elif store == "apple":
        config = PublicationRepository(
            repo=ApiContext.github_apple_repo,
            workflow=ApiContext.github_apple_workflow,
            branch=ApiContext.github_apple_branch,
        )
    else:
        raise ValueError(f"Unsupported publication store '{store}'")

    if not config.repo:
        raise ValueError(f"Publication store '{store}' is not configured")
    return config


class GitHubClient:
    @property
    def _headers(self) -> dict[str, Any]:
        if not ApiContext.github_token:
            raise ValueError("GITHUB_TOKEN is not configured")
        return {
            "Authorization": f"Bearer {ApiContext.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _repo_url(self, repo: str) -> str:
        return f"{ApiContext.github_api_url}/repos/{repo}"

    def get_branch_sha(self, *, repo: str, branch: str) -> str:
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/commits/{branch}",
            headers=self._headers,
        )
        if response.status_code != HTTPStatus.OK:
            raise ValueError(
                f"Unable to resolve branch '{branch}' of '{repo}' "
                f"(HTTP {response.status_code})"
            )
        sha = response.json.get("sha")
        if not sha:
            raise ValueError(f"No commit SHA returned for branch '{branch}'")
        return sha

    def create_tag(self, *, repo: str, tag: str, sha: str) -> bool:
        """Create a tag ref. Returns False when the tag already exists."""
        response = query_api(
            method="POST",
            url=f"{self._repo_url(repo)}/git/refs",
            headers=self._headers,
            payload={"ref": f"refs/tags/{tag}", "sha": sha},
        )
        if response.status_code == HTTPStatus.CREATED:
            return True
        if response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
            return False
        raise ValueError(
            f"Failed to create tag '{tag}' in '{repo}' "
            f"(HTTP {response.status_code}): {response.json.get('message')}"
        )

    def create_release(
        self,
        *,
        repo: str,
        tag: str,
        sha: str,
        app_name: str,
        content_version: str,
    ) -> dict[str, Any]:
        response = query_api(
            method="POST",
            url=f"{self._repo_url(repo)}/releases",
            headers=self._headers,
            payload={
                "tag_name": tag,
                "target_commitish": sha,
                "name": f"{app_name} {content_version}",
                "body": (
                    f"Branded app **{app_name}** publication.\n\n"
                    f"- Content version: `{content_version}`\n"
                    f"- Tag: `{tag}`"
                ),
                "draft": False,
                "prerelease": False,
                "make_latest": "false",
            },
        )
        if response.status_code != HTTPStatus.CREATED:
            raise ValueError(
                f"Failed to create release '{tag}' in '{repo}' "
                f"(HTTP {response.status_code}): {response.json.get('message')}"
            )
        return response.json

    def publish(
        self, *, store: str, app_name: str, content_version: str
    ) -> PublicationResult:
        """Create the tag then the release in the store's repository."""
        config = get_repository_config(store)
        sha = self.get_branch_sha(repo=config.repo, branch=config.branch)
        base_tag = get_tag_prefix(app_name=app_name, content_version=content_version)
        for build_number in range(100):
            tag = f"{base_tag}.{build_number}"
            if not self.create_tag(repo=config.repo, tag=tag, sha=sha):
                continue
            logger.info(f"Created tag '{tag}' for release on {config.repo}.")
            release = self.create_release(
                repo=config.repo,
                tag=tag,
                sha=sha,
                app_name=app_name,
                content_version=content_version,
            )
            logger.info(f"Created release for '{tag}' on {config.repo}")
            return PublicationResult(
                tag=tag,
                commit_sha=sha,
                release_id=release["id"],
                release_url=release["html_url"],
                repository=config.repo,
                workflow=config.workflow,
            )
        raise ValueError(f"Unable to find a free tag for '{base_tag}'")

    def get_run_for_publication(
        self, *, repo: str, workflow: str, tag: str, commit_sha: str
    ) -> dict[str, Any] | None:
        """Find the workflow run triggered by a release"""
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/actions/workflows/{workflow}/runs",
            headers=self._headers,
            params={"event": "release", "per_page": 100},
        )
        if response.status_code != HTTPStatus.OK:
            return None
        runs: list[dict[str, Any]] = response.json.get("workflow_runs", [])
        for run in runs:
            if run.get("head_sha") != commit_sha:
                continue
            head_branch = run.get("head_branch")
            if head_branch and head_branch != tag:
                continue
            return run
        return None

    def get_workflow_run(self, *, repo: str, run_id: int) -> dict[str, Any] | None:
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/actions/runs/{run_id}",
            headers=self._headers,
        )
        if response.status_code != HTTPStatus.OK:
            return None
        return response.json


github_client = GitHubClient()
