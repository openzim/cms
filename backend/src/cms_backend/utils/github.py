import base64
import binascii
import json
import re
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.utils.requests import query_api

CONTENT_VERSION_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})(?P<suffix>[a-z]*)$"
)

CHECK_GREEN_CONCLUSIONS = {"success", "neutral", "skipped"}


@dataclass(frozen=True)
class AppBuildRepository:
    """GitHub repository and workflow used to publish to a given store."""

    repo: str
    workflow: str
    branch: str


@dataclass
class AppBuildResult:
    tag: str
    commit_sha: str
    release_id: int
    release_url: str
    repository: str
    workflow: str


@dataclass
class AppBuildPullRequestResult:
    branch: str
    base_sha: str
    pr_number: int | None
    pr_url: str | None


@dataclass
class ChecksSummary:
    total: int = 0
    passed: int = 0
    pending: int = 0
    failed: list[str] = field(default_factory=list[str])

    @property
    def is_green(self) -> bool:
        return self.pending == 0 and not self.failed


def get_tag_prefix(*, app_name: str, content_version: str) -> str:
    """Return the tag prefix, without the build number.

    Tags follow the `<app>_<YYYY>.<MM>[suffix].<build>` convention for every
    store. The build number starts at 0 and is incremented on every attempt.
    """
    match = CONTENT_VERSION_PATTERN.fullmatch(content_version)
    if match is None:
        raise ValueError(f"Invalid content version '{content_version}'")
    return (
        f"{app_name}_{match.group('year')}.{match.group('month')}"
        f"{match.group('suffix')}"
    )


def get_repository_config(store: str) -> AppBuildRepository:
    """Get the configured repository for a build store."""
    if store == "android":
        config = AppBuildRepository(
            repo=Context.github_android_repo,
            workflow=Context.github_android_workflow,
            branch=Context.github_android_branch,
        )
    elif store == "apple":
        config = AppBuildRepository(
            repo=Context.github_apple_repo,
            workflow=Context.github_apple_workflow,
            branch=Context.github_apple_branch,
        )
    else:
        raise ValueError(f"Unsupported build store '{store}'")

    if not config.repo:
        raise ValueError(f"Build store '{store}' is not configured")
    return config


class GitHubClient:
    @property
    def _headers(self) -> dict[str, Any]:
        if not Context.github_token:
            raise ValueError("GITHUB_TOKEN is not configured")
        return {
            "Authorization": f"Bearer {Context.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _repo_url(self, repo: str) -> str:
        return f"{Context.github_api_url}/repos/{repo}"

    def get_branch_sha(self, *, repo: str, branch: str) -> str:
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/commits/{branch}",
            headers=self._headers,
        )
        if response.status_code != HTTPStatus.OK:
            raise ValueError(
                f"Unable to resolve branch '{branch}' of '{repo}' "
                f"(HTTP {response.status_code}): {response.json.get('message')}"
            )
        sha = response.json.get("sha")
        if not sha:
            raise ValueError(f"No commit SHA returned for branch '{branch}'")
        return sha

    def create_branch(self, *, repo: str, branch: str, sha: str) -> bool:
        """Create a branch ref. Returns False when it already exists."""
        response = query_api(
            method="POST",
            url=f"{self._repo_url(repo)}/git/refs",
            headers=self._headers,
            payload={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        if response.status_code == HTTPStatus.CREATED:
            return True
        if response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
            return False
        raise ValueError(
            f"Failed to create branch '{branch}' in '{repo}' "
            f"(HTTP {response.status_code}): {response.json.get('message')}"
        )

    def get_file(self, *, repo: str, path: str, ref: str) -> dict[str, Any] | None:
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/contents/{path}",
            headers=self._headers,
            params={"ref": ref},
        )
        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        if response.status_code != HTTPStatus.OK:
            raise ValueError(
                f"Unable to read '{path}' from '{repo}' "
                f"(HTTP {response.status_code}): {response.json.get('message')}"
            )
        return response.json

    def put_file(
        self,
        *,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        response = query_api(
            method="PUT",
            url=f"{self._repo_url(repo)}/contents/{path}",
            headers=self._headers,
            payload=payload,
        )
        if response.status_code not in (HTTPStatus.OK, HTTPStatus.CREATED):
            raise ValueError(
                f"Unable to write '{path}' in '{repo}' "
                f"(HTTP {response.status_code}): {response.json.get('message')}"
            )
        return response.json

    def find_open_pull_request(
        self, *, repo: str, head: str, base: str
    ) -> dict[str, Any] | None:
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/pulls",
            headers=self._headers,
            params={"state": "open", "head": head, "base": base, "per_page": 100},
        )
        if response.status_code != HTTPStatus.OK:
            return None
        pulls = cast(list[dict[str, Any]], response.json)
        branch = head.split(":", 1)[-1]
        for pull in pulls:
            if pull.get("head", {}).get("ref") == branch:
                return pull
        return pulls[0] if pulls else None

    def create_pull_request(
        self, *, repo: str, head: str, base: str, title: str, body: str
    ) -> dict[str, Any]:
        response = query_api(
            method="POST",
            url=f"{self._repo_url(repo)}/pulls",
            headers=self._headers,
            payload={
                "head": head,
                "base": base,
                "title": title,
                "body": body,
                "draft": False,
            },
        )
        if response.status_code != HTTPStatus.CREATED:
            raise ValueError(
                f"Failed to create pull request in '{repo}' "
                f"(HTTP {response.status_code}): {response.json.get('message')}"
            )
        return response.json

    def create_app_build_pull_request(
        self,
        *,
        store: str,
        app_name: str,
        content_version: str,
        zim_filename: str,
        branch: str,
        build_id: str,
    ) -> AppBuildPullRequestResult:
        """Prepare config changes and open a PR, or signal a rebuild is needed."""
        config = get_repository_config(store)
        base_sha = self.get_branch_sha(repo=config.repo, branch=config.branch)

        path = f"{app_name}/info.json"
        file_data = self.get_file(repo=config.repo, path=path, ref=config.branch)
        if file_data is None:
            raise ValueError(f"Unable to find '{path}' in '{config.repo}'")
        try:
            raw = base64.b64decode(file_data["content"]).decode("utf-8")
            info = cast(dict[str, Any], json.loads(raw))
        except (KeyError, UnicodeDecodeError, binascii.Error, ValueError) as exc:
            raise ValueError(f"Unable to read '{path}' in '{config.repo}'") from exc

        current_url = info.get("zim_url")
        if not isinstance(current_url, str) or not current_url:
            raise ValueError(f"'{path}' has no 'zim_url' to update")

        url_parts = urlsplit(current_url)
        base_path = url_parts.path.rsplit("/", 1)[0]
        new_url = urlunsplit(url_parts._replace(path=f"{base_path}/{zim_filename}"))

        if current_url == new_url:
            return AppBuildPullRequestResult(
                branch=config.branch,
                base_sha=base_sha,
                pr_number=None,
                pr_url=None,
            )

        if not self.create_branch(repo=config.repo, branch=branch, sha=base_sha):
            logger.info(f"Branch '{branch}' already exists in '{config.repo}'")

        info["zim_url"] = new_url
        self.put_file(
            repo=config.repo,
            path=path,
            content=json.dumps(info, indent=2) + "\n",
            message=f"Build {app_name} {content_version}",
            branch=branch,
            sha=file_data.get("sha"),
        )

        owner = config.repo.split("/", 1)[0]
        head = f"{owner}:{branch}"
        pull = self.find_open_pull_request(
            repo=config.repo, head=head, base=config.branch
        )
        if pull is None:
            pull = self.create_pull_request(
                repo=config.repo,
                head=head,
                base=config.branch,
                title=f"Build {app_name} {content_version}",
                body=(
                    f"Automated build of **{app_name}** `{content_version}`.\n\n"
                    f"- Content: `{zim_filename}`\n"
                    f"- CMS build: `{build_id}`\n\n"
                    "This pull request was created by the CMS."
                ),
            )

        return AppBuildPullRequestResult(
            branch=branch,
            base_sha=base_sha,
            pr_number=int(pull["number"]),
            pr_url=str(pull["html_url"]),
        )

    def get_pull_request(self, *, repo: str, number: int) -> dict[str, Any] | None:
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/pulls/{number}",
            headers=self._headers,
        )
        if response.status_code != HTTPStatus.OK:
            return None
        return response.json

    def get_checks(self, *, repo: str, ref: str) -> ChecksSummary:
        summary = ChecksSummary()
        response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/commits/{ref}/check-runs",
            headers=self._headers,
            params={"per_page": 100},
        )
        if response.status_code == HTTPStatus.OK:
            for check in response.json.get("check_runs", []):
                summary.total += 1
                if check.get("status") != "completed":
                    summary.pending += 1
                elif check.get("conclusion") in CHECK_GREEN_CONCLUSIONS:
                    summary.passed += 1
                else:
                    summary.failed.append(str(check.get("name") or "check"))

        status_response = query_api(
            method="GET",
            url=f"{self._repo_url(repo)}/commits/{ref}/status",
            headers=self._headers,
        )
        if status_response.status_code == HTTPStatus.OK:
            for status in status_response.json.get("statuses", []):
                summary.total += 1
                state = status.get("state")
                if state == "pending":
                    summary.pending += 1
                elif state == "success":
                    summary.passed += 1
                else:
                    summary.failed.append(str(status.get("context") or "status"))
        return summary

    def close_pull_request(self, *, repo: str, number: int) -> bool:
        response = query_api(
            method="PATCH",
            url=f"{self._repo_url(repo)}/pulls/{number}",
            headers=self._headers,
            payload={"state": "closed"},
        )
        return response.status_code == HTTPStatus.OK

    def cancel_workflow_run(self, *, repo: str, run_id: int) -> bool:
        response = query_api(
            method="POST",
            url=f"{self._repo_url(repo)}/actions/runs/{run_id}/cancel",
            headers=self._headers,
        )
        return response.status_code == HTTPStatus.ACCEPTED

    def merge_pull_request(self, *, repo: str, number: int, sha: str) -> bool:
        response = query_api(
            method="PUT",
            url=f"{self._repo_url(repo)}/pulls/{number}/merge",
            headers=self._headers,
            payload={"sha": sha, "merge_method": "merge"},
        )
        if response.status_code == HTTPStatus.OK:
            return bool(response.json.get("merged", True))
        if response.status_code in (
            HTTPStatus.METHOD_NOT_ALLOWED,
            HTTPStatus.CONFLICT,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ):
            logger.warning(
                f"GitHub refused to merge pull request #{number} in '{repo}' "
                f"(HTTP {response.status_code}): "
                f"{response.json.get('message')}"
            )
            return False
        raise ValueError(
            f"Failed to merge pull request #{number} in '{repo}' "
            f"(HTTP {response.status_code}): {response.json.get('message')}"
        )

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
                    f"Branded app **{app_name}** build.\n\n"
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

    def create_release_on_sha(
        self,
        *,
        repo: str,
        app_name: str,
        content_version: str,
        sha: str,
        workflow: str = "",
    ) -> AppBuildResult:
        """Create the next free tag pointing at sha and its release."""
        base_tag = get_tag_prefix(app_name=app_name, content_version=content_version)
        for build_number in range(100):
            tag = f"{base_tag}.{build_number}"
            if not self.create_tag(repo=repo, tag=tag, sha=sha):
                continue
            logger.info(f"Created tag '{tag}' for release on {repo}.")
            release = self.create_release(
                repo=repo,
                tag=tag,
                sha=sha,
                app_name=app_name,
                content_version=content_version,
            )
            logger.info(f"Created release for '{tag}' on {repo}")
            return AppBuildResult(
                tag=tag,
                commit_sha=sha,
                release_id=release["id"],
                release_url=release["html_url"],
                repository=repo,
                workflow=workflow,
            )
        raise ValueError(f"Unable to find a free tag for '{base_tag}'")

    def publish(
        self, *, store: str, app_name: str, content_version: str
    ) -> AppBuildResult:
        """Create the tag then the release in the store's repository."""
        config = get_repository_config(store)
        sha = self.get_branch_sha(repo=config.repo, branch=config.branch)
        return self.create_release_on_sha(
            repo=config.repo,
            app_name=app_name,
            content_version=content_version,
            sha=sha,
            workflow=config.workflow,
        )

    def get_run_for_build(
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
