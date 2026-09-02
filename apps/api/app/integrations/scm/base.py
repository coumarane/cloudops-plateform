from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ScmOrganization:
    external_id: str
    login: str
    name: str
    avatar_url: str = ""
    html_url: str = ""


@dataclass
class ScmRepository:
    external_id: str
    organization: str
    name: str
    full_name: str
    description: str = ""
    default_branch: str = "main"
    visibility: str = "private"
    archived: bool = False
    html_url: str = ""
    pushed_at: datetime | None = None


@dataclass
class ScmWorkflow:
    external_id: str
    repository_external_id: str
    name: str
    path: str
    state: str = "active"
    html_url: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class ScmWorkflowRun:
    external_id: str
    workflow_external_id: str
    repository_external_id: str
    branch: str
    commit_sha: str
    event: str
    actor: str
    status: str
    conclusion: str
    html_url: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    run_attempt: int = 1
    github_environment: str = ""


@dataclass
class ScmJob:
    external_id: str
    run_external_id: str
    name: str
    status: str
    conclusion: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    runner_name: str = ""
    runner_group: str = ""
    html_url: str = ""


@dataclass
class ScmVariable:
    name: str
    value: str
    scope: str
    repository_external_id: str = ""
    organization: str = ""
    github_environment: str = ""
    updated_at: datetime | None = None
    sensitive: bool = False


@dataclass
class ScmSecret:
    name: str
    scope: str
    repository_external_id: str = ""
    organization: str = ""
    github_environment: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class ScmPublicKey:
    key_id: str
    key: str


class SourceControlProvider(ABC):
    """Provider-neutral source control integration. GitHub is the first implementation."""

    name: str

    @abstractmethod
    def list_organizations(self) -> list[ScmOrganization]: ...

    @abstractmethod
    def list_repositories(self) -> list[ScmRepository]: ...

    @abstractmethod
    def list_workflows(self, repository: ScmRepository) -> list[ScmWorkflow]: ...

    @abstractmethod
    def list_workflow_runs(self, repository: ScmRepository, *, since: datetime | None = None) -> list[ScmWorkflowRun]: ...

    @abstractmethod
    def list_jobs(self, run: ScmWorkflowRun, repository: ScmRepository | None = None) -> list[ScmJob]: ...

    @abstractmethod
    def list_variables(self, repository: ScmRepository) -> list[ScmVariable]: ...

    @abstractmethod
    def list_secrets(self, repository: ScmRepository) -> list[ScmSecret]: ...

    @abstractmethod
    def put_secret(
        self,
        *,
        repository: ScmRepository,
        name: str,
        value: str,
        github_environment: str = "",
    ) -> None: ...

    @abstractmethod
    def delete_secret(self, *, repository: ScmRepository, name: str, github_environment: str = "") -> None: ...

    @abstractmethod
    def put_variable(
        self,
        *,
        repository: ScmRepository,
        name: str,
        value: str,
        github_environment: str = "",
        sensitive: bool = False,
    ) -> None: ...

    @abstractmethod
    def delete_variable(self, *, repository: ScmRepository, name: str, github_environment: str = "") -> None: ...

    def list_organization_variables(self, organization: str) -> list[ScmVariable]:
        return []

    def list_organization_secrets(self, organization: str) -> list[ScmSecret]:
        return []
