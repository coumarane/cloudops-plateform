from __future__ import annotations

from datetime import datetime

from app.core.config import settings
from app.integrations.github.auth import build_app_jwt, load_private_key
from app.integrations.github.client import GitHubClient
from app.integrations.github.exceptions import GitHubNotConfigured
from app.integrations.github.repositories import list_organizations, list_repositories
from app.integrations.github.secrets import delete_secret as gh_delete_secret
from app.integrations.github.secrets import put_secret as gh_put_secret
from app.integrations.github.secrets import list_secrets
from app.integrations.github.variables import delete_variable as gh_delete_variable
from app.integrations.github.variables import put_variable as gh_put_variable
from app.integrations.github.variables import list_variables
from app.integrations.github.workflows import list_jobs, list_workflow_runs, list_workflows
from app.integrations.scm.base import (
    ScmJob,
    ScmOrganization,
    ScmRepository,
    ScmSecret,
    ScmVariable,
    ScmWorkflow,
    ScmWorkflowRun,
    SourceControlProvider,
)


class GitHubProvider(SourceControlProvider):
    name = "github"

    def __init__(
        self,
        *,
        app_id: str | None = None,
        installation_id: str | None = None,
        private_key_ref: str | None = None,
        api_url: str | None = None,
        client: GitHubClient | None = None,
    ) -> None:
        self.app_id = app_id if app_id is not None else settings.github_app_id
        self.installation_id = installation_id if installation_id is not None else settings.github_installation_id
        self.private_key_ref = private_key_ref if private_key_ref is not None else settings.github_private_key_ref
        self.api_url = (api_url or settings.github_api_url or "https://api.github.com").rstrip("/")
        self._client = client

    def client(self) -> GitHubClient:
        if self._client is not None:
            return self._client
        if not self.app_id or not self.installation_id or not self.private_key_ref:
            raise GitHubNotConfigured("GitHub App is not configured")
        private_key = load_private_key(self.private_key_ref)
        jwt_token = build_app_jwt(self.app_id, private_key)
        bootstrap = GitHubClient(api_url=self.api_url, token=jwt_token)
        token_payload = bootstrap.request("POST", f"/app/installations/{self.installation_id}/access_tokens") or {}
        token = str(token_payload.get("token") or "")
        if not token:
            raise GitHubNotConfigured("GitHub installation token was empty")
        self._client = GitHubClient(api_url=self.api_url, token=token, http=bootstrap._http)
        return self._client

    def list_organizations(self) -> list[ScmOrganization]:
        return list_organizations(self.client())

    def list_repositories(self) -> list[ScmRepository]:
        return list_repositories(self.client())

    def list_workflows(self, repository: ScmRepository) -> list[ScmWorkflow]:
        return list_workflows(self.client(), repository)

    def list_workflow_runs(self, repository: ScmRepository, *, since: datetime | None = None) -> list[ScmWorkflowRun]:
        return list_workflow_runs(self.client(), repository, since=since)

    def list_jobs(self, run: ScmWorkflowRun, repository: ScmRepository | None = None) -> list[ScmJob]:
        if repository is None:
            repository = ScmRepository(
                external_id=run.repository_external_id,
                organization="",
                name="",
                full_name="",
            )
        return list_jobs(self.client(), repository, run)

    def list_variables(self, repository: ScmRepository) -> list[ScmVariable]:
        return list_variables(self.client(), repository)

    def list_secrets(self, repository: ScmRepository) -> list[ScmSecret]:
        return list_secrets(self.client(), repository)

    def put_secret(self, *, repository: ScmRepository, name: str, value: str, github_environment: str = "") -> None:
        gh_put_secret(self.client(), repository, name=name, value=value, github_environment=github_environment)

    def delete_secret(self, *, repository: ScmRepository, name: str, github_environment: str = "") -> None:
        gh_delete_secret(self.client(), repository, name=name, github_environment=github_environment)

    def put_variable(
        self,
        *,
        repository: ScmRepository,
        name: str,
        value: str,
        github_environment: str = "",
        sensitive: bool = False,
    ) -> None:
        gh_put_variable(self.client(), repository, name=name, value=value, github_environment=github_environment)

    def delete_variable(self, *, repository: ScmRepository, name: str, github_environment: str = "") -> None:
        gh_delete_variable(self.client(), repository, name=name, github_environment=github_environment)

    def list_organization_variables(self, organization: str) -> list[ScmVariable]:
        from app.integrations.github.variables import list_organization_variables

        return list_organization_variables(self.client(), organization)

    def list_organization_secrets(self, organization: str) -> list[ScmSecret]:
        from app.integrations.github.secrets import list_organization_secrets

        return list_organization_secrets(self.client(), organization)


def get_scm_provider(*, client: GitHubClient | None = None) -> SourceControlProvider:
    return GitHubProvider(client=client)
