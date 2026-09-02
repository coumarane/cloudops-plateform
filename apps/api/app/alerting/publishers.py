from __future__ import annotations

from app.alerting.models import AlertSignal
from app.alerting.service import publish, resolve_source
from sqlalchemy.orm import Session


def publish_health(session: Session, *, kind: str, row, title: str, severity: str, recovered: bool = False, extra: dict | None = None):
    source_type = "cluster" if kind.startswith("CLUSTER") else "application"
    source_id = (row.cluster_id if source_type == "cluster" else (row.application_id or getattr(row, "id", ""))) or kind
    return publish(
        session,
        AlertSignal(
            alert_type=kind,
            source_type=source_type,
            source_id=source_id,
            title=title,
            summary=getattr(row, "summary", "") or title,
            severity=severity or "HIGH",
            provider=getattr(row, "provider", "") or "AWS",
            region=getattr(row, "region", "") or "EMEA",
            account_id=getattr(row, "account_alias", "") or "",
            environment_id=getattr(row, "environment_id", "") or "",
            environment=getattr(row, "environment", "") or "",
            application_id=getattr(row, "application_id", "") or "",
            cluster_id=getattr(row, "cluster_id", "") or "",
            recovered=recovered,
            resolution_reason="application recovered" if recovered else "",
            metadata=extra or {},
        ),
    )


def recover_health(session: Session, *, application_id: str, environment_id: str, reason: str = "application recovered") -> int:
    return resolve_source(
        session,
        application_id=application_id,
        environment_id=environment_id,
        reason=reason,
    )


def publish_certificate(session: Session, *, kind: str, row, title: str, summary: str, severity: str, recovered: bool = False, extra: dict | None = None):
    return publish(
        session,
        AlertSignal(
            alert_type=kind,
            source_type="certificate",
            source_id=row.id,
            title=title,
            summary=summary,
            severity=severity,
            provider=row.provider or "AWS",
            region=row.platform_region or "EMEA",
            account_id=row.account_alias or "",
            environment_id=getattr(row, "environment_id", "") or "",
            environment=row.environment or "DEV",
            application_id=row.application_id or "",
            cluster_id=row.cluster_name or "",
            recovered=recovered,
            resolution_reason="certificate renewed" if recovered else "",
            metadata={"related": {"certificateId": row.id}, **(extra or {})},
        ),
    )


def recover_certificate(session: Session, *, certificate_id: str) -> int:
    return resolve_source(session, source_type="certificate", source_id=certificate_id, reason="certificate renewed")


def publish_pipeline(session: Session, *, pipeline, run, environment: str, severity: str, recovered: bool = False, env_row=None):
    return publish(
        session,
        AlertSignal(
            alert_type="PIPELINE_FAILED",
            source_type="pipeline",
            source_id=pipeline.id,
            title=f"{pipeline.name} failed",
            summary=f"Pipeline {pipeline.name} {run.status}",
            severity=severity or "HIGH",
            provider=getattr(env_row, "provider", "") if env_row is not None else "AWS",
            region=getattr(env_row, "platform_region", "") if env_row is not None else "EMEA",
            account_id=getattr(env_row, "account_alias", "") if env_row is not None else "",
            environment_id=run.environment_id or "",
            environment=environment,
            application_id=run.application_id or pipeline.application_id or "",
            recovered=recovered,
            resolution_reason="pipeline recovered" if recovered else "",
            metadata={"related": {"pipelineId": pipeline.id, "pipelineRunId": run.id, "deploymentId": run.deployment_id}},
        ),
    )


def publish_github(session: Session, *, repository, workflow, run, environment: str, severity: str, recovered: bool = False, env_row=None):
    return publish(
        session,
        AlertSignal(
            alert_type="GITHUB_WORKFLOW_FAILED",
            source_type="github",
            source_id=workflow.id,
            title=f"{workflow.name} failed",
            summary=f"Workflow {workflow.name} failed in {repository.full_name if hasattr(repository, 'full_name') else repository.name}",
            severity=severity or "HIGH",
            provider=getattr(env_row, "provider", "") if env_row is not None else "AWS",
            region=getattr(env_row, "platform_region", "") if env_row is not None else "EMEA",
            account_id=getattr(env_row, "account_alias", "") if env_row is not None else "",
            environment_id=run.cloudops_environment_id or "",
            environment=environment,
            application_id=getattr(run, "application_id", "") or "",
            recovered=recovered,
            resolution_reason="workflow recovered" if recovered else "",
            metadata={"related": {"repositoryId": repository.id, "workflowId": workflow.id, "runId": run.id}},
        ),
    )
