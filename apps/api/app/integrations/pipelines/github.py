from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GithubRepositoryRow, GithubWorkflowJobRow, GithubWorkflowRunRow, GithubWorkflowRow
from app.integrations.pipelines.base import (
    PipelineProvider,
    ProviderPipeline,
    ProviderPipelineJob,
    ProviderPipelineRun,
    ProviderPipelineStage,
)
from app.integrations.pipelines.status import ACTIVE_STATUSES, normalize_github


class GitHubActionsPipelineProvider(PipelineProvider):
    """Projects already-synced GitHub Actions rows. Does not call the GitHub API."""

    key = "github-actions"
    display_name = "GitHub Actions"

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_pipelines(self) -> list[ProviderPipeline]:
        return [self._pipeline(row) for row in self.session.scalars(select(GithubWorkflowRow))]

    def get_pipeline(self, external_id: str) -> ProviderPipeline | None:
        row = self.session.scalar(
            select(GithubWorkflowRow).where(
                (GithubWorkflowRow.github_id == external_id) | (GithubWorkflowRow.id == external_id)
            )
        )
        return self._pipeline(row) if row else None

    def list_runs(
        self,
        pipeline: ProviderPipeline,
        *,
        since: datetime | None = None,
        running_only: bool = False,
    ) -> list[ProviderPipelineRun]:
        workflow = self._workflow(pipeline.external_id)
        if workflow is None:
            return []
        query = select(GithubWorkflowRunRow).where(GithubWorkflowRunRow.workflow_id == workflow.id)
        rows = list(self.session.scalars(query))
        runs = [self._run(row) for row in rows]
        if since is not None:
            runs = [item for item in runs if (item.started_at or item.completed_at) and (item.started_at or item.completed_at) >= since]
        if running_only:
            runs = [item for item in runs if normalize_github(item.status, item.result) in ACTIVE_STATUSES]
        return runs

    def get_run(self, pipeline: ProviderPipeline, external_run_id: str) -> ProviderPipelineRun | None:
        row = self.session.scalar(
            select(GithubWorkflowRunRow).where(
                (GithubWorkflowRunRow.github_id == external_run_id) | (GithubWorkflowRunRow.id == external_run_id)
            )
        )
        return self._run(row) if row else None

    def list_stages(self, run: ProviderPipelineRun) -> list[ProviderPipelineStage]:
        jobs = self.list_jobs(run)
        seen: dict[str, ProviderPipelineStage] = {}
        for job in jobs:
            name = _stage_name(job.name)
            if name in seen:
                continue
            seen[name] = ProviderPipelineStage(
                external_id=name.lower().replace(" ", "-"),
                run_external_id=run.external_id,
                name=name,
                status=job.status,
                result=job.result,
                html_url=job.html_url,
                started_at=job.started_at,
                completed_at=job.completed_at,
                sort_order=_stage_order(name),
            )
        return sorted(seen.values(), key=lambda item: item.sort_order)

    def list_jobs(self, run: ProviderPipelineRun) -> list[ProviderPipelineJob]:
        github_run = self.session.scalar(
            select(GithubWorkflowRunRow).where(
                (GithubWorkflowRunRow.github_id == run.external_id) | (GithubWorkflowRunRow.id == run.external_id)
            )
        )
        if github_run is None:
            return []
        return [
            ProviderPipelineJob(
                external_id=job.github_id,
                run_external_id=run.external_id,
                name=job.name,
                status=job.github_status or job.status,
                result=job.github_conclusion,
                html_url=job.html_url,
                stage_external_id=_stage_name(job.name).lower().replace(" ", "-"),
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            for job in self.session.scalars(select(GithubWorkflowJobRow).where(GithubWorkflowJobRow.run_id == github_run.id))
        ]

    def _workflow(self, external_id: str) -> GithubWorkflowRow | None:
        return self.session.scalar(
            select(GithubWorkflowRow).where(
                (GithubWorkflowRow.github_id == external_id) | (GithubWorkflowRow.id == external_id)
            )
        )

    def _pipeline(self, row: GithubWorkflowRow) -> ProviderPipeline:
        repo = self.session.get(GithubRepositoryRow, row.repository_id)
        return ProviderPipeline(
            external_id=row.github_id,
            name=row.name,
            repository_external_id=repo.github_id if repo else row.repository_id,
            default_branch=repo.default_branch if repo else "",
            enabled=row.state == "active",
            html_url=row.html_url,
            metadata={"githubWorkflowId": row.id, "path": row.path, "repositoryId": row.repository_id},
        )

    def _run(self, row: GithubWorkflowRunRow) -> ProviderPipelineRun:
        workflow = self.session.get(GithubWorkflowRow, row.workflow_id)
        return ProviderPipelineRun(
            external_id=row.github_id,
            pipeline_external_id=workflow.github_id if workflow else "",
            branch=row.branch,
            commit_sha=row.commit_sha,
            trigger=row.event,
            actor=row.actor,
            status=row.github_status or row.status,
            result=row.github_conclusion,
            html_url=row.html_url,
            started_at=row.started_at,
            completed_at=row.completed_at,
            environment_name=row.github_environment,
            metadata={
                "githubRunId": row.id,
                "repositoryId": row.repository_id,
                "applicationId": row.application_id,
                "deploymentId": row.deployment_id,
                "clusterId": row.cluster_id,
                "cloudopsEnvironmentId": row.cloudops_environment_id,
                "normalizedStatus": row.status,
            },
        )


def _stage_name(job_name: str) -> str:
    lower = (job_name or "").lower()
    if "deploy" in lower:
        return "Deploy"
    if "scan" in lower or "security" in lower:
        return "Security Scan"
    if "test" in lower:
        return "Test"
    if "build" in lower:
        return "Build"
    return "Jobs"


def _stage_order(name: str) -> int:
    order = {"Build": 10, "Test": 20, "Security Scan": 30, "Jobs": 40, "Deploy": 50}
    return order.get(name, 40)
