from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    GithubRepositoryRow,
    PipelineAlertRow,
    PipelineApplicationMappingRow,
    PipelineAuditRow,
    PipelineEnvironmentMappingRow,
    PipelineJobRow,
    PipelineProviderRow,
    PipelineRow,
    PipelineRunRow,
    PipelineStageRow,
)
from app.domain.models import ActivityItem, ApplicationRecord, AuditEvent, OperationalAlert, RecentFailure, RunRecord
from app.integrations.pipelines.status import FAILED, RUNNING, SUCCEEDED, catalog_result
from app.services.github_presenters import environment_label
from app.services.mappers import _age


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def provider_dump(row: PipelineProviderRow) -> dict:
    return {
        "id": row.id,
        "key": row.key,
        "name": row.name,
        "organization": row.organization,
        "project": row.project,
        "baseUrl": row.base_url,
        "authRef": row.auth_ref,
        "enabled": row.enabled,
        "status": row.status,
        "lastAttemptedSyncAt": _iso(row.last_attempted_sync_at),
        "lastSuccessfulSyncAt": _iso(row.last_successful_sync_at),
        "lastError": row.last_error,
        "lastErrorClass": row.last_error_class,
    }


def mapping_dump(session: Session, row: PipelineEnvironmentMappingRow) -> dict:
    return {
        "id": row.id,
        "pipelineId": row.pipeline_id,
        "environmentId": row.environment_id,
        "branchPattern": row.branch_pattern,
        "stageName": row.stage_name,
        "active": row.active,
        "priority": row.priority,
        **environment_label(session, row.environment_id),
    }


def latest_run(session: Session, pipeline_id: str) -> PipelineRunRow | None:
    return session.scalar(
        select(PipelineRunRow).where(PipelineRunRow.pipeline_id == pipeline_id).order_by(PipelineRunRow.started_at.desc())
    )


def pipeline_dump(session: Session, row: PipelineRow) -> dict:
    provider = session.get(PipelineProviderRow, row.provider_id)
    runs = list(session.scalars(select(PipelineRunRow).where(PipelineRunRow.pipeline_id == row.id)))
    completed = [item for item in runs if item.status in {SUCCEEDED, FAILED}]
    success = sum(1 for item in completed if item.status == SUCCEEDED)
    durations = [item.duration_seconds for item in completed if item.duration_seconds]
    latest = latest_run(session, row.id)
    repo = session.get(GithubRepositoryRow, row.repository_id) if row.repository_id else None
    mappings = list(
        session.scalars(select(PipelineEnvironmentMappingRow).where(PipelineEnvironmentMappingRow.pipeline_id == row.id))
    )
    apps = [
        link.application_id
        for link in session.scalars(select(PipelineApplicationMappingRow).where(PipelineApplicationMappingRow.pipeline_id == row.id))
    ]
    env_label = environment_label(session, latest.environment_id) if latest else environment_label(session, "")
    return {
        "id": row.id,
        "providerId": row.provider_id,
        "providerKey": provider.key if provider else "",
        "providerName": provider.name if provider else "",
        "externalId": row.external_id,
        "name": row.name,
        "repositoryId": row.repository_id,
        "repository": repo.full_name if repo else "",
        "applicationId": row.application_id or (apps[0] if apps else ""),
        "applicationIds": apps,
        "defaultBranch": row.default_branch,
        "enabled": row.enabled,
        "htmlUrl": row.html_url,
        "lastSyncedAt": _iso(row.last_synced_at),
        "latestRun": run_dump(session, latest) if latest else None,
        "successRate": round(100 * success / len(completed), 1) if completed else None,
        "averageDurationSeconds": int(sum(durations) / len(durations)) if durations else None,
        "mappedEnvironments": [mapping_dump(session, item) for item in mappings],
        **env_label,
    }


def run_dump(session: Session, row: PipelineRunRow | None) -> dict | None:
    if row is None:
        return None
    pipeline = session.get(PipelineRow, row.pipeline_id)
    provider = session.get(PipelineProviderRow, pipeline.provider_id) if pipeline else None
    repo = session.get(GithubRepositoryRow, row.repository_id) if row.repository_id else None
    label = environment_label(session, row.environment_id)
    return {
        "id": row.id,
        "pipelineId": row.pipeline_id,
        "pipelineName": pipeline.name if pipeline else "",
        "providerKey": provider.key if provider else "",
        "providerName": provider.name if provider else "",
        "externalRunId": row.external_run_id,
        "branch": row.branch,
        "commitSha": row.commit_sha,
        "version": row.version,
        "trigger": row.trigger,
        "actor": row.actor,
        "status": row.status,
        "providerStatus": row.provider_status,
        "startedAt": _iso(row.started_at),
        "completedAt": _iso(row.completed_at),
        "durationSeconds": row.duration_seconds,
        "externalUrl": row.external_url,
        "applicationId": row.application_id,
        "deploymentId": row.deployment_id,
        "repositoryId": row.repository_id,
        "repository": repo.full_name if repo else "",
        "clusterId": row.cluster_id,
        "age": _age(row.completed_at or row.started_at) if (row.completed_at or row.started_at) else "",
        **label,
    }


def stage_dump(row: PipelineStageRow) -> dict:
    return {
        "id": row.id,
        "runId": row.run_id,
        "name": row.name,
        "status": row.status,
        "providerStatus": row.provider_status,
        "startedAt": _iso(row.started_at),
        "completedAt": _iso(row.completed_at),
        "durationSeconds": row.duration_seconds,
        "sortOrder": row.sort_order,
        "htmlUrl": row.html_url,
    }


def job_dump(row: PipelineJobRow) -> dict:
    return {
        "id": row.id,
        "runId": row.run_id,
        "stageId": row.stage_id,
        "name": row.name,
        "status": row.status,
        "providerStatus": row.provider_status,
        "startedAt": _iso(row.started_at),
        "completedAt": _iso(row.completed_at),
        "durationSeconds": row.duration_seconds,
        "htmlUrl": row.html_url,
    }


def overview_dump(session: Session) -> dict:
    runs = list(session.scalars(select(PipelineRunRow)))
    now = datetime.now(timezone.utc)
    today = [item for item in runs if item.started_at and (_aware(item.started_at).date() == now.date())]
    failed = [item for item in runs if item.status == FAILED]
    failed_prd = []
    durations = [item.duration_seconds for item in runs if item.duration_seconds and item.status == SUCCEEDED]
    for item in failed:
        label = environment_label(session, item.environment_id)
        if label.get("environment") == "PRD":
            failed_prd.append(item)
    return {
        "pipelineRunsToday": len(today),
        "runningPipelines": sum(1 for item in runs if item.status == RUNNING),
        "failedPipelines": len(failed),
        "failedPrdPipelines": len(failed_prd),
        "averageDeploymentDurationSeconds": int(sum(durations) / len(durations)) if durations else 0,
        "recentFailures": [
            run_dump(session, item)
            for item in sorted(failed, key=lambda row: _aware(row.completed_at or row.started_at), reverse=True)[:8]
        ],
    }


def to_run_record(session: Session, row: PipelineRunRow) -> RunRecord:
    payload = run_dump(session, row) or {}
    provider = payload.get("provider") or "AWS"
    region = payload.get("region") or "EMEA"
    environment = payload.get("environment") or "DEV"
    return RunRecord(
        id=row.id,
        name=payload.get("pipelineName") or "pipeline",
        detail=payload.get("repository") or payload.get("branch") or "",
        result=catalog_result(row.status),  # type: ignore[arg-type]
        age=payload.get("age") or "",
        provider=provider,  # type: ignore[arg-type]
        region=region,  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        cluster=row.cluster_id or "",
        source="github" if payload.get("providerKey") == "github-actions" else "mock",
        kind="pipeline-run",
        correlationId=row.external_run_id,
        jobStatus=row.status,
        href=f"/pipelines?run={row.id}",
    )


def to_recent_failure(session: Session, row: PipelineRunRow) -> RecentFailure:
    payload = run_dump(session, row) or {}
    return RecentFailure(
        id=row.id,
        kind="pipeline",
        name=payload.get("pipelineName") or "pipeline",
        provider=payload.get("provider") or "AWS",  # type: ignore[arg-type]
        region=payload.get("region") or "EMEA",  # type: ignore[arg-type]
        environment=payload.get("environment") or "DEV",  # type: ignore[arg-type]
        age=payload.get("age") or "",
        href=f"/pipelines?run={row.id}",
    )


def to_pipeline_alert(session: Session, row: PipelineAlertRow) -> OperationalAlert:
    run = session.get(PipelineRunRow, row.run_id) if row.run_id else None
    pipeline = session.get(PipelineRow, row.pipeline_id) if row.pipeline_id else None
    environment_id = run.environment_id if run else ""
    label = environment_label(session, environment_id)
    environment = row.environment or label.get("environment") or "DEV"
    severity = row.severity.upper()
    catalog = "critical" if severity in {"CRITICAL", "HIGH"} else "warning" if severity == "MEDIUM" else "info"
    return OperationalAlert(
        id=row.id,
        severity=catalog,  # type: ignore[arg-type]
        title=row.title or "Pipeline failed",
        objectName=(pipeline.name if pipeline else row.pipeline_id),
        provider=label.get("provider") or "AWS",  # type: ignore[arg-type]
        region=label.get("region") or "EMEA",  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        age=_age(row.created_at),
        href=f"/pipelines?run={row.run_id}" if row.run_id else "/pipelines",
    )


def to_pipeline_audit(row: PipelineAuditRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        event=row.action.replace("_", " ").title(),
        actor=row.actor,
        objectName=row.object_name or "pipeline",
        detail=row.detail,
        age=_age(row.created_at),
        provider="AWS",
        region="EMEA",
        environment=row.environment or "DEV",  # type: ignore[arg-type]
    )


def to_activity(session: Session, row: PipelineRunRow) -> ActivityItem:
    pipeline = session.get(PipelineRow, row.pipeline_id)
    provider = session.get(PipelineProviderRow, pipeline.provider_id) if pipeline else None
    return ActivityItem(
        title=f"{pipeline.name if pipeline else 'pipeline'} {row.status}",
        detail=f"{provider.key if provider else 'pipeline'} · {row.branch or '—'}",
        age=_age(row.completed_at or row.started_at),
        href=f"/pipelines?run={row.id}",
    )


def apply_pipeline(session: Session, item: ApplicationRecord) -> ApplicationRecord:
    link = session.scalar(
        select(PipelineApplicationMappingRow).where(PipelineApplicationMappingRow.application_id == item.id)
    )
    if link is None:
        link = session.scalar(
            select(PipelineApplicationMappingRow).where(PipelineApplicationMappingRow.application_id == item.name)
        )
    pipeline = session.get(PipelineRow, link.pipeline_id) if link else None
    if pipeline is None:
        pipeline = session.scalar(select(PipelineRow).where(PipelineRow.application_id.in_((item.id, item.name))))
    if pipeline is None:
        return item
    latest = latest_run(session, pipeline.id)
    provider = session.get(PipelineProviderRow, pipeline.provider_id)
    label = environment_label(session, latest.environment_id) if latest else {}
    source_env = None
    if label.get("provider"):
        source_env = f"{label.get('provider')} / {label.get('region')} / {label.get('environment')}"
    return item.model_copy(
        update={
            "pipelineId": pipeline.id,
            "pipelineName": pipeline.name,
            "pipelineProvider": provider.key if provider else None,
            "latestPipelineRunId": latest.id if latest else None,
            "latestPipelineStatus": latest.status if latest else None,
            "latestDeploymentStatus": latest.status if latest else item.latestDeploymentStatus,
            "sourceEnvironment": source_env or item.sourceEnvironment,
            "deploymentId": (latest.deployment_id if latest else None) or item.deploymentId,
            "workflowRunId": item.workflowRunId or (latest.id if latest else None),
        }
    )
