from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ApplicationHealthRow,
    HealthAlertRow,
    HealthCheckDefinitionRow,
    HealthCheckResultRow,
    HealthIncidentRow,
    ResourceHealthRow,
)
from app.db.repository import utcnow
from app.integrations.health.status import CRITICAL, DEGRADED, HEALTHY, UNHEALTHY, UNKNOWN, catalog_status
from app.services.github_presenters import environment_label
from app.services.mappers import _age


def _scope(session: Session, environment_id: str) -> dict:
    label = environment_label(session, environment_id) if environment_id else {}
    return {
        "provider": label.get("provider") or "",
        "region": label.get("region") or "",
        "environment": label.get("environment") or "",
        "environmentId": environment_id,
    }


def resource_dump(session: Session, row: ResourceHealthRow) -> dict:
    scope = _scope(session, row.environment_id)
    return {
        "id": row.id,
        "resourceType": row.resource_type,
        "name": row.resource_name,
        "namespace": row.namespace,
        "clusterId": row.cluster_id,
        "applicationId": row.application_id,
        "status": row.status,
        "summary": row.summary,
        "checkType": row.check_type,
        "errorCategory": row.error_category,
        "desired": row.desired,
        "ready": row.ready,
        "available": row.available,
        "unavailable": row.unavailable,
        "restartCount": row.restart_count,
        "reason": row.reason,
        "lastCheckedAt": row.last_checked_at.isoformat() if row.last_checked_at else None,
        "lastAttemptedAt": row.last_attempted_at.isoformat() if row.last_attempted_at else None,
        "lastSuccessfulAt": row.last_successful_at.isoformat() if row.last_successful_at else None,
        "provider": row.provider or scope["provider"],
        "region": row.region or scope["region"],
        "environment": row.environment or scope["environment"],
    }


def application_dump(session: Session, row: ApplicationHealthRow) -> dict:
    resources = [
        resource_dump(session, item)
        for item in session.scalars(
            select(ResourceHealthRow).where(
                ResourceHealthRow.application_id == row.application_id,
                ResourceHealthRow.environment_id == row.environment_id,
            )
        )
    ]
    evidence = []
    try:
        evidence = json.loads(row.evidence_json or "[]")
    except json.JSONDecodeError:
        evidence = []
    correlation = {}
    try:
        correlation = json.loads(row.correlation_json or "{}")
    except json.JSONDecodeError:
        correlation = {}
    latest_run = (correlation.get("pipelineRuns") or [None])[0]
    return {
        "id": row.id,
        "applicationId": row.application_id,
        "name": row.application_name or row.application_id,
        "status": row.status,
        "summary": row.summary,
        "likelyCause": row.likely_cause,
        "evidence": evidence,
        "correlation": correlation,
        "consecutiveUnhealthy": row.consecutive_unhealthy,
        "consecutiveHealthy": row.consecutive_healthy,
        "workload": next((item for item in resources if item["resourceType"] in {"deployment", "statefulset", "daemonset"}), None),
        "pods": [item for item in resources if item["resourceType"] == "pod"],
        "ingress": next((item for item in resources if item["resourceType"] == "ingress"), None),
        "endpoint": next((item for item in resources if item["resourceType"] == "http_endpoint"), None),
        "certificateStatus": row.certificate_status,
        "latestDeployment": {
            "status": row.deployment_status,
            "runId": (latest_run or {}).get("id"),
            "commitSha": (latest_run or {}).get("commitSha"),
            "startedAt": (latest_run or {}).get("startedAt"),
        },
        "latestPipelineRun": latest_run,
        "desiredReplicas": row.desired_replicas,
        "availableReplicas": row.available_replicas,
        "crashloop": row.crashloop,
        "failedPods": row.failed_pods,
        "restartCount": row.restart_count,
        "httpStatus": row.http_status,
        "ingressStatus": row.ingress_status,
        "clusterStatus": row.cluster_status,
        "pipelineStatus": row.pipeline_status,
        "lastAttemptedAt": row.last_attempted_at.isoformat() if row.last_attempted_at else None,
        "lastSuccessfulAt": row.last_successful_at.isoformat() if row.last_successful_at else None,
        "errorCategory": row.error_category,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "provider": row.provider,
        "region": row.region,
        "environment": row.environment,
        "clusterId": row.cluster_id,
        "resources": resources,
    }


def incident_dump(session: Session, row: HealthIncidentRow) -> dict:
    resources = []
    try:
        resources = json.loads(row.affected_resources_json or "[]")
    except json.JSONDecodeError:
        resources = []
    return {
        "id": row.id,
        "applicationId": row.application_id,
        "status": row.status,
        "severity": row.severity,
        "rootSymptom": row.root_symptom,
        "affectedResources": resources,
        "openedAt": row.opened_at.isoformat() if row.opened_at else None,
        "acknowledgedAt": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "acknowledgedBy": row.acknowledged_by,
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
        "age": _age(row.opened_at),
        "provider": row.provider,
        "region": row.region,
        "environment": row.environment,
        "environmentId": row.environment_id,
    }


def result_dump(row: HealthCheckResultRow) -> dict:
    return {
        "id": row.id,
        "definitionId": row.definition_id,
        "applicationId": row.application_id,
        "checkType": row.check_type,
        "status": row.status,
        "latencyMs": row.latency_ms,
        "statusCode": row.status_code,
        "summary": row.summary,
        "errorCategory": row.error_category,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "catalogStatus": catalog_status(row.status),
    }


def overview_dump(session: Session) -> dict:
    apps = list(session.scalars(select(ApplicationHealthRow)))
    incidents = [
        item
        for item in session.scalars(select(HealthIncidentRow))
        if item.status in {"OPEN", "ACKNOWLEDGED"}
    ]
    clusters = list(session.scalars(select(ResourceHealthRow).where(ResourceHealthRow.resource_type == "cluster")))
    return {
        "healthyApplications": sum(1 for item in apps if item.status == HEALTHY),
        "degradedApplications": sum(1 for item in apps if item.status == DEGRADED),
        "unhealthyApplications": sum(1 for item in apps if item.status == UNHEALTHY),
        "criticalApplications": sum(1 for item in apps if item.status == CRITICAL),
        "unknownApplications": sum(1 for item in apps if item.status == UNKNOWN),
        "unhealthyClusters": sum(1 for item in clusters if item.status in {UNHEALTHY, CRITICAL}),
        "openIncidents": len(incidents),
        "applications": len(apps),
        "lastSynced": utcnow().isoformat(),
    }


def environment_health_dump(session: Session, environment_id: str) -> dict:
    apps = list(session.scalars(select(ApplicationHealthRow).where(ApplicationHealthRow.environment_id == environment_id)))
    clusters = list(
        session.scalars(select(ResourceHealthRow).where(ResourceHealthRow.environment_id == environment_id, ResourceHealthRow.resource_type == "cluster"))
    )
    incidents = [
        item
        for item in session.scalars(select(HealthIncidentRow).where(HealthIncidentRow.environment_id == environment_id))
        if item.status in {"OPEN", "ACKNOWLEDGED"}
    ]
    overall = UNKNOWN
    if apps:
        from app.integrations.health.status import worst

        overall = worst(*(item.status for item in apps))
    elif clusters:
        from app.integrations.health.status import worst

        overall = worst(*(item.status for item in clusters))
    sample = apps[0] if apps else None
    return {
        "environmentId": environment_id,
        "provider": sample.provider if sample else "",
        "region": sample.region if sample else "",
        "environment": sample.environment if sample else "",
        "overall": overall,
        "clustersHealthy": sum(1 for item in clusters if item.status == HEALTHY),
        "clustersTotal": len(clusters),
        "applicationsTotal": len(apps),
        "applicationsHealthy": sum(1 for item in apps if item.status == HEALTHY),
        "applicationsDegraded": sum(1 for item in apps if item.status == DEGRADED),
        "applicationsUnhealthy": sum(1 for item in apps if item.status == UNHEALTHY),
        "applicationsCritical": sum(1 for item in apps if item.status == CRITICAL),
        "openIncidents": len(incidents),
        "applications": [application_dump(session, item) for item in apps],
    }


def definition_dump(row: HealthCheckDefinitionRow) -> dict:
    return {
        "id": row.id,
        "checkType": row.check_type,
        "name": row.name,
        "enabled": row.enabled,
        "intervalSeconds": row.interval_seconds,
        "timeoutSeconds": row.timeout_seconds,
        "retries": row.retries,
        "severity": row.severity,
        "environmentId": row.environment_id,
        "applicationId": row.application_id,
        "urlConfigured": bool(row.url),
        "method": row.method,
        "lastAttemptedAt": row.last_attempted_at.isoformat() if row.last_attempted_at else None,
        "lastSuccessfulAt": row.last_successful_at.isoformat() if row.last_successful_at else None,
        "lastErrorCategory": row.last_error_category,
    }


def to_health_check_record(session: Session, row: HealthCheckResultRow):
    from app.domain.models import HealthCheckRecord

    label = environment_label(session, row.environment_id)
    definition = session.get(HealthCheckDefinitionRow, row.definition_id) if row.definition_id else None
    provider = label.get("provider") or "AWS"
    region = label.get("region") or "EMEA"
    environment = label.get("environment") or "DEV"
    return HealthCheckRecord(
        id=row.id,
        name=(definition.name if definition else row.check_type),
        target=row.application_id or row.cluster_id or row.check_type,
        checkType=row.check_type,
        status=catalog_status(row.status),  # type: ignore[arg-type]
        lastRun=_age(row.created_at),
        provider=provider,  # type: ignore[arg-type]
        region=region,  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        cluster=row.cluster_id or "",
    )


def to_health_alert(session: Session, row: HealthAlertRow):
    from app.domain.models import OperationalAlert

    app = session.scalar(select(ApplicationHealthRow).where(ApplicationHealthRow.application_id == row.application_id))
    provider = (app.provider if app else None) or "AWS"
    region = (app.region if app else None) or "EMEA"
    environment = row.environment or (app.environment if app else "DEV")
    severity = "critical" if row.severity in {"HIGH", "CRITICAL"} else "warning" if row.severity == "MEDIUM" else "info"
    return OperationalAlert(
        id=row.id,
        severity=severity,  # type: ignore[arg-type]
        title=row.title or row.kind,
        objectName=row.application_id or row.cluster_id or row.kind,
        provider=provider,  # type: ignore[arg-type]
        region=region,  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        age=_age(row.created_at),
        href=f"/health-checks?app={row.application_id}" if row.application_id else "/health-checks",
    )
