from __future__ import annotations

from datetime import datetime

from app.integrations.github.client import GitHubClient
from app.integrations.github.mapper import parse_datetime
from app.integrations.scm.base import ScmJob, ScmRepository, ScmWorkflow, ScmWorkflowRun


def list_workflows(client: GitHubClient, repository: ScmRepository) -> list[ScmWorkflow]:
    workflows: list[ScmWorkflow] = []
    for payload in client.paginate(f"/repos/{repository.full_name}/actions/workflows", item_key="workflows"):
        workflows.append(
            ScmWorkflow(
                external_id=str(payload.get("id") or payload.get("path")),
                repository_external_id=repository.external_id,
                name=str(payload.get("name") or payload.get("path") or "workflow"),
                path=str(payload.get("path") or ""),
                state=str(payload.get("state") or "active"),
                html_url=str(payload.get("html_url") or ""),
                created_at=parse_datetime(payload.get("created_at")),
                updated_at=parse_datetime(payload.get("updated_at")),
            )
        )
    return workflows


def list_workflow_runs(
    client: GitHubClient, repository: ScmRepository, *, since: datetime | None = None
) -> list[ScmWorkflowRun]:
    params = {"created": f">={since.date().isoformat()}"} if since else None
    runs: list[ScmWorkflowRun] = []
    for payload in client.paginate(f"/repos/{repository.full_name}/actions/runs", params=params, item_key="workflow_runs"):
        head = payload.get("head_commit") or {}
        actor = payload.get("actor") or payload.get("triggering_actor") or {}
        runs.append(
            ScmWorkflowRun(
                external_id=str(payload.get("id")),
                workflow_external_id=str(payload.get("workflow_id") or ""),
                repository_external_id=repository.external_id,
                branch=str(payload.get("head_branch") or ""),
                commit_sha=str(payload.get("head_sha") or head.get("id") or ""),
                event=str(payload.get("event") or ""),
                actor=str(actor.get("login") or ""),
                status=str(payload.get("status") or ""),
                conclusion=str(payload.get("conclusion") or ""),
                html_url=str(payload.get("html_url") or ""),
                started_at=parse_datetime(payload.get("run_started_at") or payload.get("created_at")),
                completed_at=parse_datetime(payload.get("updated_at") if payload.get("status") == "completed" else None),
                run_attempt=int(payload.get("run_attempt") or 1),
                github_environment=_environment_from_run(payload),
            )
        )
    return runs


def list_jobs(client: GitHubClient, repository: ScmRepository, run: ScmWorkflowRun) -> list[ScmJob]:
    jobs: list[ScmJob] = []
    for payload in client.paginate(
        f"/repos/{repository.full_name}/actions/runs/{run.external_id}/jobs", item_key="jobs"
    ):
        jobs.append(
            ScmJob(
                external_id=str(payload.get("id")),
                run_external_id=run.external_id,
                name=str(payload.get("name") or "job"),
                status=str(payload.get("status") or ""),
                conclusion=str(payload.get("conclusion") or ""),
                started_at=parse_datetime(payload.get("started_at")),
                completed_at=parse_datetime(payload.get("completed_at")),
                runner_name=str(payload.get("runner_name") or ""),
                runner_group=str(payload.get("runner_group_name") or payload.get("labels") or ""),
                html_url=str(payload.get("html_url") or ""),
            )
        )
    return jobs


def _environment_from_run(payload: dict) -> str:
    for key in ("environment", "github_environment"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict) and value.get("name"):
            return str(value["name"])
    return ""
