from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting.models import AlertStatus, SEVERITY_RANK, normalize_severity, ui_severity
from app.db.models import (
    AlertEventRow,
    AlertRow,
    AlertRuleRow,
    AlertRoutingRuleRow,
    MaintenanceWindowRow,
    NotificationDeliveryRow,
    NotificationDestinationRow,
    NotificationPolicyRow,
    NotificationPolicyStepRow,
)
from app.services.mappers import _age


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _extra(row: AlertRow) -> dict:
    try:
        payload = json.loads(row.extra_json or "{}")
    except Exception:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def alert_dump(row: AlertRow) -> dict:
    extra = _extra(row)
    resource = row.application_id or row.source_id or row.title
    return {
        "id": row.id,
        "alertType": row.alert_type,
        "sourceType": row.source_type,
        "sourceId": row.source_id,
        "provider": row.provider or "AWS",
        "region": row.region or "EMEA",
        "accountId": row.account_id,
        "environmentId": row.environment_id,
        "environment": row.environment or "DEV",
        "applicationId": row.application_id,
        "clusterId": row.cluster_id,
        "severity": row.severity,
        "uiSeverity": ui_severity(row.severity),
        "status": row.status,
        "title": row.title,
        "summary": row.summary,
        "fingerprint": row.fingerprint,
        "firstSeenAt": _iso(row.first_seen_at),
        "lastSeenAt": _iso(row.last_seen_at),
        "occurrenceCount": row.occurrence_count,
        "acknowledgedAt": _iso(row.acknowledged_at),
        "acknowledgedBy": row.acknowledged_by,
        "acknowledgedComment": row.acknowledged_comment,
        "resolvedAt": _iso(row.resolved_at),
        "resolutionReason": row.resolution_reason,
        "correlationId": row.correlation_id,
        "metadata": extra,
        "ruleId": row.rule_id,
        "policyId": row.policy_id,
        "objectName": resource,
        "age": _age(row.last_seen_at or row.first_seen_at),
        "href": f"/alerts?selected={row.id}",
        "related": extra.get("related") if isinstance(extra.get("related"), dict) else {},
    }


def event_dump(row: AlertEventRow) -> dict:
    return {
        "id": row.id,
        "alertId": row.alert_id,
        "eventType": row.event_type,
        "title": row.title,
        "detail": row.detail,
        "actor": row.actor,
        "createdAt": _iso(row.created_at),
    }


def delivery_dump(row: NotificationDeliveryRow, destination: NotificationDestinationRow | None = None) -> dict:
    return {
        "id": row.id,
        "alertId": row.alert_id,
        "destinationId": row.destination_id,
        "destinationName": destination.name if destination else "",
        "providerType": destination.provider_type if destination else "",
        "notificationType": row.notification_type,
        "status": row.status,
        "attempt": row.attempt,
        "sentAt": _iso(row.sent_at),
        "failedAt": _iso(row.failed_at),
        "errorCategory": row.error_category,
        "externalMessageId": row.external_message_id,
        "detail": row.detail,
    }


def _config(row: NotificationDestinationRow) -> dict:
    try:
        payload = json.loads(row.config_json or "{}")
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        return {}
    redacted = dict(payload)
    for key in ("url", "webhookUrl", "token", "password", "smtp_password", "secret"):
        redacted.pop(key, None)
    return redacted


def destination_dump(row: NotificationDestinationRow) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "providerType": row.provider_type,
        "configurationReference": row.configuration_reference,
        "hasSecret": bool(row.configuration_reference),
        "config": _config(row),
        "enabled": row.enabled,
        "description": row.description,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def policy_dump(row: NotificationPolicyRow, steps: list[NotificationPolicyStepRow] | None = None) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "initialEnabled": row.initial_enabled,
        "repeatAfterSeconds": row.repeat_after_seconds,
        "escalateAfterSeconds": row.escalate_after_seconds,
        "recoveryEnabled": row.recovery_enabled,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
        "steps": [
            {
                "id": step.id,
                "delaySeconds": step.delay_seconds,
                "destinationId": step.destination_id,
                "stepType": step.step_type,
                "enabled": step.enabled,
            }
            for step in (steps or [])
        ],
    }


def rule_dump(row: AlertRuleRow) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "alertType": row.alert_type,
        "enabled": row.enabled,
        "providerFilter": row.provider_filter,
        "regionFilter": row.region_filter,
        "environmentFilter": row.environment_filter,
        "applicationFilter": row.application_filter,
        "severity": row.severity,
        "minimumOccurrences": row.minimum_occurrences,
        "evaluationWindowSeconds": row.evaluation_window_seconds,
        "notificationPolicyId": row.notification_policy_id,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def route_dump(row: AlertRoutingRuleRow) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "enabled": row.enabled,
        "providerFilter": row.provider_filter,
        "regionFilter": row.region_filter,
        "accountFilter": row.account_filter,
        "environmentFilter": row.environment_filter,
        "applicationFilter": row.application_filter,
        "severityFilter": row.severity_filter,
        "alertTypeFilter": row.alert_type_filter,
        "destinationId": row.destination_id,
        "policyId": row.policy_id,
        "createdAt": _iso(row.created_at),
    }


def window_dump(row: MaintenanceWindowRow) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "scope": row.scope,
        "provider": row.provider,
        "region": row.region,
        "environment": row.environment,
        "application": row.application,
        "startsAt": _iso(row.starts_at),
        "endsAt": _iso(row.ends_at),
        "reason": row.reason,
        "changeTicket": row.change_ticket,
        "createdBy": row.created_by,
        "enabled": row.enabled,
    }


def sort_alerts(rows: list[AlertRow], order: str | None) -> list[AlertRow]:
    key = (order or "last_seen").strip().lower().replace("-", "_")
    if key in {"first_seen", "firstseen"}:
        return sorted(rows, key=lambda row: row.first_seen_at or datetime.min, reverse=True)
    if key in {"environment", "env"}:
        return sorted(rows, key=lambda row: ((row.environment or "").upper() != "PRD", row.environment or "", row.last_seen_at or datetime.min), reverse=False)
    if key == "severity":
        return sorted(
            rows,
            key=lambda row: (
                -SEVERITY_RANK.get(normalize_severity(row.severity), 0),
                row.last_seen_at or datetime.min,
            ),
            reverse=False,
        )
    return sorted(rows, key=lambda row: row.last_seen_at or datetime.min, reverse=True)


def kpi_counts(rows: list[AlertRow]) -> dict[str, int]:
    return {
        "critical": sum(1 for row in rows if normalize_severity(row.severity) == "CRITICAL" and row.status != AlertStatus.RESOLVED),
        "high": sum(1 for row in rows if normalize_severity(row.severity) == "HIGH" and row.status != AlertStatus.RESOLVED),
        "medium": sum(1 for row in rows if normalize_severity(row.severity) == "MEDIUM" and row.status != AlertStatus.RESOLVED),
        "acknowledged": sum(1 for row in rows if row.status == AlertStatus.ACKNOWLEDGED),
        "suppressed": sum(1 for row in rows if row.status == AlertStatus.SUPPRESSED),
        "open": sum(1 for row in rows if row.status == AlertStatus.OPEN),
        "prdCritical": sum(
            1
            for row in rows
            if row.status in {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED}
            and normalize_severity(row.severity) == "CRITICAL"
            and (row.environment or "").upper() == "PRD"
        ),
    }


def related_context(session: Session, row: AlertRow) -> dict:
    extra = _extra(row)
    related = extra.get("related") if isinstance(extra.get("related"), dict) else {}
    from app.db.models import AcmCertificateRow, HealthIncidentRow, PipelineRow, PipelineRunRow

    incident = None
    if related.get("incidentId"):
        incident = session.get(HealthIncidentRow, related["incidentId"])
    elif row.application_id:
        incident = session.scalar(
            select(HealthIncidentRow).where(
                HealthIncidentRow.application_id == row.application_id,
                HealthIncidentRow.status.in_(("OPEN", "ACKNOWLEDGED")),
            )
        )
    certificate = session.get(AcmCertificateRow, related["certificateId"]) if related.get("certificateId") else None
    if certificate is None and row.source_type == "certificate":
        certificate = session.get(AcmCertificateRow, row.source_id)
    pipeline_run = session.get(PipelineRunRow, related["pipelineRunId"]) if related.get("pipelineRunId") else None
    pipeline = session.get(PipelineRow, related["pipelineId"]) if related.get("pipelineId") else None
    return {
        "incident": {"id": incident.id, "title": incident.root_symptom, "status": incident.status} if incident is not None else None,
        "certificate": {"id": certificate.id, "domain": certificate.domain_name, "status": certificate.expiry_status} if certificate is not None else None,
        "pipeline": {"id": pipeline.id, "name": pipeline.name} if pipeline is not None else None,
        "pipelineRun": {"id": pipeline_run.id, "status": pipeline_run.status} if pipeline_run is not None else None,
        "deploymentId": related.get("deploymentId") or (pipeline_run.deployment_id if pipeline_run is not None else ""),
    }
