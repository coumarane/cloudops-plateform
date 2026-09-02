from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CloudEnvironmentRow,
    GithubAlertRow,
    GithubApplicationRepositoryRow,
    GithubAuditRow,
    GithubEnvironmentMappingRow,
    GithubOrganizationRow,
    GithubRepositoryRow,
    GithubSecretRow,
    GithubVariableRow,
    GithubWorkflowJobRow,
    GithubWorkflowRunRow,
    GithubWorkflowRow,
)
from app.domain.models import ApplicationRecord, AuditEvent, OperationalAlert, RecentFailure, RunRecord
from app.integrations.github.mapper import CANCELLED, FAILED, RUNNING, SUCCEEDED
from app.services.mappers import _age


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def environment_label(session: Session, environment_id: str) -> dict:
    if not environment_id:
        return {"cloudopsEnvironmentId": "", "provider": None, "region": None, "environment": None}
    row = session.get(CloudEnvironmentRow, environment_id)
    if row is None:
        return {"cloudopsEnvironmentId": environment_id, "provider": None, "region": None, "environment": None}
    return {
        "cloudopsEnvironmentId": row.id,
        "provider": row.provider,
        "region": row.platform_region,
        "environment": row.environment,
    }


def organization_dump(row: GithubOrganizationRow) -> dict:
    return {
        "id": row.id,
        "login": row.login,
        "name": row.name or row.login,
        "avatarUrl": row.avatar_url,
        "htmlUrl": row.html_url,
        "status": row.status,
        "lastSynchronizedAt": _iso(row.last_synchronized_at),
        "provider": "github",
    }


def repository_dump(session: Session, row: GithubRepositoryRow) -> dict:
    apps = [
        link.application_id
        for link in session.scalars(
            select(GithubApplicationRepositoryRow).where(GithubApplicationRepositoryRow.repository_id == row.id)
        )
    ]
    mappings = list(
        session.scalars(select(GithubEnvironmentMappingRow).where(GithubEnvironmentMappingRow.github_repository_id == row.id))
    )
    unmapped = 0
    mapped = []
    for mapping in mappings:
        item = {
            "id": mapping.id,
            "githubEnvironment": mapping.github_environment,
            "active": mapping.active,
            **environment_label(session, mapping.cloudops_environment_id),
        }
        mapped.append(item)
        if not mapping.cloudops_environment_id or not mapping.active:
            unmapped += 1
    return {
        "id": row.id,
        "organization": row.organization,
        "name": row.name,
        "fullName": row.full_name,
        "description": row.description,
        "defaultBranch": row.default_branch,
        "visibility": row.visibility,
        "archived": row.archived,
        "htmlUrl": row.html_url,
        "pushedAt": _iso(row.pushed_at),
        "lastSynchronizedAt": _iso(row.last_synchronized_at),
        "applicationIds": apps,
        "environments": mapped,
        "unmappedEnvironments": unmapped,
        "provider": "github",
    }


def workflow_dump(session: Session, row: GithubWorkflowRow) -> dict:
    runs = list(
        session.scalars(
            select(GithubWorkflowRunRow)
            .where(GithubWorkflowRunRow.workflow_id == row.id)
            .order_by(GithubWorkflowRunRow.started_at.desc())
        )
    )
    latest = runs[0] if runs else None
    completed = [item for item in runs if item.status in {SUCCEEDED, FAILED, CANCELLED}]
    success = sum(1 for item in completed if item.status == SUCCEEDED)
    durations = [item.duration_seconds for item in completed if item.duration_seconds]
    return {
        "id": row.id,
        "repositoryId": row.repository_id,
        "name": row.name,
        "path": row.path,
        "state": row.state,
        "htmlUrl": row.html_url,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
        "lastSynchronizedAt": _iso(row.last_synchronized_at),
        "latestRun": run_dump(session, latest) if latest else None,
        "successRate": round(100 * success / len(completed), 1) if completed else None,
        "averageDurationSeconds": int(sum(durations) / len(durations)) if durations else None,
        "provider": "github",
    }


def run_dump(session: Session, row: GithubWorkflowRunRow | None) -> dict | None:
    if row is None:
        return None
    workflow = session.get(GithubWorkflowRow, row.workflow_id)
    repo = session.get(GithubRepositoryRow, row.repository_id)
    return {
        "id": row.id,
        "workflowId": row.workflow_id,
        "repositoryId": row.repository_id,
        "repository": repo.full_name if repo else "",
        "workflow": workflow.name if workflow else "",
        "workflowPath": workflow.path if workflow else "",
        "branch": row.branch,
        "commitSha": row.commit_sha,
        "event": row.event,
        "actor": row.actor,
        "status": row.status,
        "githubStatus": row.github_status,
        "githubConclusion": row.github_conclusion,
        "startedAt": _iso(row.started_at),
        "completedAt": _iso(row.completed_at),
        "durationSeconds": row.duration_seconds,
        "runAttempt": row.run_attempt,
        "htmlUrl": row.html_url,
        "githubEnvironment": row.github_environment,
        "applicationId": row.application_id,
        "deploymentId": row.deployment_id,
        "clusterId": row.cluster_id,
        "age": _age(row.started_at or row.completed_at) if (row.started_at or row.completed_at) else "",
        **environment_label(session, row.cloudops_environment_id),
        "scmProvider": "github",
    }


def job_dump(row: GithubWorkflowJobRow) -> dict:
    return {
        "id": row.id,
        "runId": row.run_id,
        "name": row.name,
        "status": row.status,
        "githubStatus": row.github_status,
        "githubConclusion": row.github_conclusion,
        "startedAt": _iso(row.started_at),
        "completedAt": _iso(row.completed_at),
        "durationSeconds": row.duration_seconds,
        "runnerName": row.runner_name,
        "runnerType": row.runner_type,
        "htmlUrl": row.html_url,
        "provider": "github",
    }


def variable_dump(session: Session, row: GithubVariableRow) -> dict:
    repo = session.get(GithubRepositoryRow, row.repository_id)
    return {
        "id": row.id,
        "name": row.name,
        "scope": row.scope,
        "repositoryId": row.repository_id,
        "repository": repo.full_name if repo else "",
        "organization": row.organization,
        "githubEnvironment": row.github_environment,
        "value": row.value_masked,
        "sensitive": row.sensitive,
        "updatedAt": _iso(row.updated_at),
        **environment_label(session, row.cloudops_environment_id),
        "scmProvider": "github",
    }


def secret_dump(session: Session, row: GithubSecretRow) -> dict:
    repo = session.get(GithubRepositoryRow, row.repository_id)
    return {
        "id": row.id,
        "name": row.name,
        "scope": row.scope,
        "repositoryId": row.repository_id,
        "repository": repo.full_name if repo else "",
        "organization": row.organization,
        "githubEnvironment": row.github_environment,
        "value": "••••••••••••",
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
        **environment_label(session, row.cloudops_environment_id),
        "scmProvider": "github",
    }


def overview_dump(session: Session) -> dict:
    repos = list(session.scalars(select(GithubRepositoryRow)))
    workflows = list(session.scalars(select(GithubWorkflowRow)))
    runs = list(session.scalars(select(GithubWorkflowRunRow)))
    mappings = list(session.scalars(select(GithubEnvironmentMappingRow)))
    now = datetime.now(timezone.utc)
    failed_24h = 0
    for run in runs:
        if run.status != FAILED:
            continue
        stamp = run.completed_at or run.started_at
        if stamp is not None and stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp and (now - stamp).total_seconds() <= 86400:
            failed_24h += 1
    linked = {link.repository_id for link in session.scalars(select(GithubApplicationRepositoryRow))}
    return {
        "repositories": len(repos),
        "activeWorkflows": sum(1 for item in workflows if item.state == "active"),
        "runningWorkflows": sum(1 for item in runs if item.status == RUNNING),
        "failedWorkflows": sum(1 for item in runs if item.status == FAILED),
        "failedWorkflowsLast24h": failed_24h,
        "succeededWorkflows": sum(1 for item in runs if item.status == SUCCEEDED),
        "unmappedRepositories": sum(1 for item in repos if item.id not in linked),
        "unmappedGithubEnvironments": sum(1 for item in mappings if not item.cloudops_environment_id or not item.active),
        "recentFailures": [
            run_dump(session, run)
            for run in sorted(
                (item for item in runs if item.status == FAILED),
                key=lambda item: _aware(item.completed_at or item.started_at),
                reverse=True,
            )[:8]
        ],
    }


def _scope_for_environment(session: Session, environment_id: str) -> tuple[str, str, str]:
    label = environment_label(session, environment_id)
    provider = label.get("provider") or "AWS"
    region = label.get("region") or "EMEA"
    environment = label.get("environment") or "DEV"
    return provider, region, environment


def to_run_record(session: Session, row: GithubWorkflowRunRow) -> RunRecord:
    workflow = session.get(GithubWorkflowRow, row.workflow_id)
    repo = session.get(GithubRepositoryRow, row.repository_id)
    provider, region, environment = _scope_for_environment(session, row.cloudops_environment_id)
    if row.status == SUCCEEDED:
        result = "Succeeded"
    elif row.status in {FAILED, CANCELLED}:
        result = "Failed"
    else:
        result = "Running"
    return RunRecord(
        id=row.id,
        name=(workflow.name if workflow else "workflow"),
        detail=(repo.full_name if repo else ""),
        result=result,  # type: ignore[arg-type]
        age=_age(row.completed_at or row.started_at),
        provider=provider,  # type: ignore[arg-type]
        region=region,  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        cluster=row.cluster_id or "",
        source="github",
        kind="github-workflow-run",
        correlationId=row.github_id,
        jobStatus=row.status,
        href=f"/github?run={row.id}",
    )


def to_recent_failure(session: Session, row: GithubWorkflowRunRow) -> RecentFailure:
    workflow = session.get(GithubWorkflowRow, row.workflow_id)
    repo = session.get(GithubRepositoryRow, row.repository_id)
    provider, region, environment = _scope_for_environment(session, row.cloudops_environment_id)
    name = repo.name if repo else (workflow.name if workflow else "workflow")
    return RecentFailure(
        id=row.id,
        kind="github",
        name=name,
        provider=provider,  # type: ignore[arg-type]
        region=region,  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        age=_age(row.completed_at or row.started_at),
        href=f"/github?run={row.id}",
    )


def to_github_alert(session: Session, row: GithubAlertRow) -> OperationalAlert:
    repo = session.get(GithubRepositoryRow, row.repository_id)
    run = session.get(GithubWorkflowRunRow, row.run_id)
    environment_id = run.cloudops_environment_id if run else ""
    provider, region, environment = _scope_for_environment(session, environment_id)
    if row.environment:
        environment = row.environment
    severity = row.severity.upper()
    catalog = "critical" if severity in {"CRITICAL", "HIGH"} else "warning" if severity == "MEDIUM" else "info"
    return OperationalAlert(
        id=row.id,
        severity=catalog,  # type: ignore[arg-type]
        title=row.title or "GitHub workflow failed",
        objectName=(repo.full_name if repo else row.workflow_id),
        provider=provider,  # type: ignore[arg-type]
        region=region,  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        age=_age(row.created_at),
        href=f"/github?run={row.run_id}" if row.run_id else "/github",
    )


def to_github_audit(row: GithubAuditRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        event=row.action.replace("_", " ").title(),
        actor=row.actor,
        objectName=row.object_name or "github",
        detail=row.detail,
        age=_age(row.created_at),
        provider="AWS",
        region="EMEA",
        environment=row.environment or "DEV",  # type: ignore[arg-type]
    )


def apply_source_control(session: Session, item: ApplicationRecord) -> ApplicationRecord:
    link = session.scalar(
        select(GithubApplicationRepositoryRow).where(GithubApplicationRepositoryRow.application_id == item.id)
    )
    if link is None:
        link = session.scalar(
            select(GithubApplicationRepositoryRow).where(GithubApplicationRepositoryRow.application_id == item.name)
        )
    if link is None:
        return item
    repo = session.get(GithubRepositoryRow, link.repository_id)
    if repo is None:
        return item
    latest = session.scalar(
        select(GithubWorkflowRunRow)
        .where(GithubWorkflowRunRow.repository_id == repo.id)
        .order_by(GithubWorkflowRunRow.started_at.desc())
    )
    workflow = session.get(GithubWorkflowRow, latest.workflow_id) if latest else None
    label = environment_label(session, latest.cloudops_environment_id) if latest else {}
    source_env = None
    if label.get("provider"):
        source_env = f"{label.get('provider')} / {label.get('region')} / {label.get('environment')}"
    return item.model_copy(
        update={
            "repositoryId": repo.id,
            "repository": repo.full_name,
            "branch": latest.branch if latest else repo.default_branch,
            "commitSha": (latest.commit_sha[:7] if latest and latest.commit_sha else None),
            "workflow": (workflow.path or workflow.name) if workflow else None,
            "latestWorkflowStatus": latest.status if latest else None,
            "latestDeploymentStatus": latest.status if latest else None,
            "sourceEnvironment": source_env,
            "workflowRunId": latest.id if latest else None,
            "deploymentId": latest.deployment_id if latest else None,
        }
    )
