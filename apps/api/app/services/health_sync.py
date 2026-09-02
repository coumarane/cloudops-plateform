from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger, sanitize_text
from app.core.metrics import inc, observe_duration, set_gauge
from app.db.models import (
    AcmCertificateRow,
    ApplicationDependencyRow,
    ApplicationHealthRow,
    ApplicationResourceMappingRow,
    CloudEnvironmentRow,
    EksClusterHealthRow,
    EksClusterRow,
    HealthAlertRow,
    HealthAuditRow,
    HealthCheckDefinitionRow,
    HealthCheckResultRow,
    HealthIncidentRow,
    HealthScanLockRow,
    HealthTimelineEventRow,
    PipelineRunRow,
    PlatformJobRow,
    ResourceHealthRow,
)
from app.db.repository import InventoryRepository, utcnow
from app.db.session import SessionLocal
from app.integrations.health.normalize import (
    NormalizedResource,
    cluster_health_status,
    normalize_cluster,
    snapshot_from_resources,
)
from app.integrations.health.rules import HealthSignals, aggregate_application
from app.integrations.health.status import (
    APP_K8S_INSTANCE,
    APP_K8S_NAME,
    CRITICAL,
    DEGRADED,
    HEALTHY,
    INCIDENT_ACKNOWLEDGED,
    INCIDENT_OPEN,
    INCIDENT_RESOLVED,
    UNHEALTHY,
    UNKNOWN,
    worst,
)
from app.notifications.factory import get_notification_provider
from app.providers.common.certificates import EXPIRED
from app.services.endpoint_tls import EndpointPolicyError
from app.services.health_http import probe_http

logger = get_logger(__name__)

SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _id(prefix: str, *parts: str) -> str:
    digest = sha256("|".join(str(part) for part in parts).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _json(data) -> str:
    return json.dumps(data or {}, default=str)[:8000]


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def environment_class(environment: str | None) -> str:
    value = (environment or "").upper()
    if value in {"INT/TST", "INT-TST", "INT", "TST"}:
        return "INT/TST"
    if value in {"DEV", "UAT", "NPD", "PRD"}:
        return value
    return value or "UNKNOWN"


def notification_floor(environment: str) -> str:
    klass = environment_class(environment)
    mapping = {
        "DEV": settings.health_alert_dev,
        "INT/TST": settings.health_alert_int_tst,
        "UAT": settings.health_alert_uat,
        "NPD": settings.health_alert_npd,
        "PRD": settings.health_alert_prd,
    }
    return (mapping.get(klass) or "").upper()


def health_to_alert_severity(status: str) -> str:
    if status == CRITICAL:
        return "CRITICAL"
    if status == UNHEALTHY:
        return "HIGH"
    if status == DEGRADED:
        return "MEDIUM"
    return "LOW"


def meets_notification_floor(environment: str, severity: str) -> bool:
    floor = notification_floor(environment)
    if not floor:
        return False
    return SEVERITY_RANK.get(severity, 0) >= SEVERITY_RANK.get(floor, 99)


def record_audit(session: Session, action: str, *, actor: str, object_name: str = "", detail: str = "", result: str = "succeeded") -> None:
    session.add(
        HealthAuditRow(
            id=str(uuid4()),
            action=action,
            actor=actor,
            object_name=object_name,
            result=result,
            detail=sanitize_text(detail)[:2000],
            created_at=utcnow(),
        )
    )


def add_timeline(
    session: Session,
    *,
    application_id: str,
    environment_id: str,
    event_type: str,
    title: str,
    detail: str = "",
    href: str = "",
    when: datetime | None = None,
) -> None:
    detail = sanitize_text(detail)[:512]
    existing = session.scalar(
        select(HealthTimelineEventRow)
        .where(
            HealthTimelineEventRow.application_id == application_id,
            HealthTimelineEventRow.environment_id == environment_id,
            HealthTimelineEventRow.event_type == event_type,
            HealthTimelineEventRow.title == title,
            HealthTimelineEventRow.detail == detail,
        )
        .order_by(HealthTimelineEventRow.created_at.desc())
    )
    if existing is not None:
        return
    session.add(
        HealthTimelineEventRow(
            id=str(uuid4()),
            application_id=application_id,
            environment_id=environment_id,
            event_type=event_type,
            title=title,
            detail=detail,
            href=href,
            created_at=when or utcnow(),
        )
    )


def acquire_lock(session: Session, environment_id: str, owner: str) -> bool:
    now = utcnow()
    existing = session.get(HealthScanLockRow, environment_id)
    if existing and _aware(existing.locked_until) and _aware(existing.locked_until) > now:
        return False
    until = now + timedelta(seconds=settings.health_scan_lock_seconds)
    if existing:
        existing.owner = owner
        existing.locked_until = until
    else:
        session.add(HealthScanLockRow(environment_id=environment_id, owner=owner, locked_until=until))
    session.flush()
    return True


def resources_from_snapshot(snapshot, *, cluster_name: str) -> list[NormalizedResource]:
    reachable = bool(snapshot.kubernetes_api_reachable)
    items = [
        normalize_cluster(
            reachable=reachable,
            version="",
            cluster_status=snapshot.control_plane_status,
            detail=snapshot.detail,
        )
    ]
    node_status = HEALTHY
    if snapshot.node_count and snapshot.ready_node_count < snapshot.node_count:
        node_status = DEGRADED if snapshot.ready_node_count else UNHEALTHY
    items.append(
        NormalizedResource(
            resource_type="node",
            name="_summary",
            status=CRITICAL if not reachable else node_status,
            summary=f"{snapshot.ready_node_count}/{snapshot.node_count} ready",
            desired=snapshot.node_count,
            ready=snapshot.ready_node_count,
            check_type="NODE_READY",
        )
    )
    pod_status = HEALTHY
    if snapshot.crashloop_backoff_count:
        pod_status = UNHEALTHY
    elif snapshot.unhealthy_pod_count or snapshot.pending_pod_count:
        pod_status = DEGRADED
    items.append(
        NormalizedResource(
            resource_type="pod",
            name="_summary",
            status=CRITICAL if not reachable else pod_status,
            summary=f"{snapshot.pod_count} pods, {snapshot.unhealthy_pod_count} unhealthy",
            desired=snapshot.pod_count,
            restart_count=snapshot.crashloop_backoff_count,
            reason="CrashLoopBackOff" if snapshot.crashloop_backoff_count else "",
            check_type="POD_STATUS",
        )
    )
    deploy_status = HEALTHY
    if snapshot.unavailable_deployment_count:
        deploy_status = UNHEALTHY
    items.append(
        NormalizedResource(
            resource_type="deployment",
            name="_summary",
            status=CRITICAL if not reachable else deploy_status,
            summary=f"{snapshot.unavailable_deployment_count} unavailable",
            unavailable=snapshot.unavailable_deployment_count,
            check_type="DEPLOYMENT_AVAILABILITY",
        )
    )
    if snapshot.stateful_set_unhealthy_count:
        items.append(
            NormalizedResource(
                resource_type="statefulset",
                name="_summary",
                status=UNHEALTHY,
                summary=f"{snapshot.stateful_set_unhealthy_count} unhealthy",
                check_type="DEPLOYMENT_AVAILABILITY",
            )
        )
    if snapshot.failed_job_count:
        items.append(
            NormalizedResource(
                resource_type="job",
                name="_summary",
                status=UNHEALTHY,
                summary=f"{snapshot.failed_job_count} failed",
                check_type="POD_STATUS",
            )
        )
    if snapshot.ingress_unhealthy_count:
        items.append(
            NormalizedResource(
                resource_type="ingress",
                name="_summary",
                status=UNHEALTHY,
                summary=f"{snapshot.ingress_unhealthy_count} unhealthy",
                check_type="INGRESS_REACHABILITY",
            )
        )
    return items


def _parse_selector(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for part in (raw or "").split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            labels[key.strip()] = value.strip()
    return labels


def match_application(
    session: Session,
    resource: NormalizedResource,
    *,
    environment_id: str,
    cluster_id: str,
) -> str:
    mappings = list(
        session.scalars(
            select(ApplicationResourceMappingRow).where(
                ApplicationResourceMappingRow.active.is_(True),
                ApplicationResourceMappingRow.environment_id.in_((environment_id, "")),
            )
        )
    )
    for mapping in mappings:
        if mapping.cluster_id and mapping.cluster_id != cluster_id:
            continue
        if mapping.namespace and mapping.namespace != resource.namespace:
            continue
        if mapping.resource_type and mapping.resource_type != resource.resource_type:
            continue
        if mapping.resource_name and mapping.resource_name != resource.name:
            continue
        selector = _parse_selector(mapping.label_selector)
        if selector and any(resource.labels.get(key) != value for key, value in selector.items()):
            continue
        return mapping.application_id
    name_label = resource.labels.get(APP_K8S_NAME) or resource.labels.get(APP_K8S_INSTANCE)
    if name_label:
        return f"app-{name_label}"
    return ""


def persist_resources(
    session: Session,
    resources: list[NormalizedResource],
    *,
    cluster_id: str,
    environment: CloudEnvironmentRow,
    application_id: str = "",
    definition_id: str = "",
    prune_stale: bool = True,
    prune_types: frozenset[str] | None = None,
) -> list[ResourceHealthRow]:
    now = utcnow()
    rows: list[ResourceHealthRow] = []
    for resource in resources:
        mapped_app = application_id or match_application(
            session, resource, environment_id=environment.id, cluster_id=cluster_id
        )
        row_id = _id("rh", cluster_id, resource.resource_type, resource.namespace, resource.name)
        row = session.get(ResourceHealthRow, row_id)
        if row is None:
            row = ResourceHealthRow(id=row_id, resource_type=resource.resource_type, resource_name=resource.name)
            session.add(row)
        row.namespace = resource.namespace
        row.cluster_id = cluster_id
        row.environment_id = environment.id
        row.application_id = mapped_app
        row.provider = environment.provider
        row.region = environment.platform_region
        row.environment = environment.environment
        row.status = resource.status
        row.summary = sanitize_text(resource.summary)[:512]
        row.check_type = resource.check_type
        row.error_category = resource.error_category
        row.desired = resource.desired
        row.ready = resource.ready
        row.available = resource.available
        row.unavailable = resource.unavailable
        row.restart_count = resource.restart_count
        row.reason = resource.reason[:128]
        row.last_checked_at = now
        row.last_attempted_at = now
        if resource.status not in {UNKNOWN} and resource.error_category != "connectivity":
            row.last_successful_at = now
        session.add(
            HealthCheckResultRow(
                id=str(uuid4()),
                definition_id=definition_id,
                resource_id=row_id,
                application_id=mapped_app,
                environment_id=environment.id,
                cluster_id=cluster_id,
                check_type=resource.check_type or resource.resource_type.upper(),
                status=resource.status,
                latency_ms=0,
                summary=sanitize_text(resource.summary)[:512],
                error_category=resource.error_category,
                created_at=now,
            )
        )
        rows.append(row)
    if not prune_stale:
        return rows
    seen = {item.id for item in rows}
    stale_query = select(ResourceHealthRow).where(ResourceHealthRow.cluster_id == cluster_id)
    if prune_types:
        stale_query = stale_query.where(ResourceHealthRow.resource_type.in_(tuple(prune_types)))
    for existing in list(session.scalars(stale_query)):
        if existing.id not in seen:
            session.delete(existing)
    return rows


def ingest_cluster_inventory(
    session: Session,
    *,
    environment: CloudEnvironmentRow,
    cluster: EksClusterRow,
    resources: list[NormalizedResource],
    error_category: str = "",
) -> None:
    now = utcnow()
    persist_resources(session, resources, cluster_id=cluster.id, environment=environment)
    environment.last_attempted_scan_at = now
    environment.last_health_at = now
    if error_category:
        environment.last_error = sanitize_text(error_category)[:500]
        environment.last_error_class = error_category
        environment.last_error_at = now
    else:
        environment.last_successful_scan_at = now
        environment.last_error = ""
        environment.last_error_class = ""
    labels = {
        "provider": environment.provider.lower(),
        "region": environment.platform_region.lower(),
        "environment_class": environment_class(environment.environment),
        "health_status": cluster_health_status(snapshot_from_resources(resources, cluster_arn=cluster.arn, control_plane_status=cluster.cluster_status)) if resources else UNKNOWN,
    }
    inc("cloudops_health_checks_total", {**labels, "health_status": "ok" if not error_category else "failed"})
    if error_category:
        inc("cloudops_health_check_failures_total", {**labels, "health_status": "failed"})


def ingest_snapshot(session: Session, cluster: EksClusterRow, snapshot, environment: CloudEnvironmentRow) -> None:
    resources = resources_from_snapshot(snapshot, cluster_name=cluster.name)
    ingest_cluster_inventory(session, environment=environment, cluster=cluster, resources=resources)


def split_health_scan_item(item) -> tuple[str, object, list]:
    """Accept 2-tuples (id, snapshot) or 3-tuples (id, snapshot, resources)."""
    if not isinstance(item, tuple) or len(item) < 2:
        raise TypeError("health scan item must be a (cluster_id, snapshot[, resources]) tuple")
    cluster_id, snapshot = item[0], item[1]
    resources = item[2] if len(item) >= 3 else []
    if not isinstance(resources, list):
        resources = []
    return str(cluster_id), snapshot, resources


def persist_account_health(account, items, repo) -> int:
    """Store cluster snapshots and, when present, per-resource Kubernetes inventory."""
    from app.topology.models import environment_scope_id

    for item in items:
        cluster_id, snapshot, resources = split_health_scan_item(item)
        repo.upsert_health(cluster_id, snapshot)
        cluster = repo.session.get(EksClusterRow, cluster_id)
        if cluster is None:
            continue
        env = repo.session.get(CloudEnvironmentRow, environment_scope_id(account.alias, cluster.environment))
        if env is None:
            env = repo.environment_row(cluster.provider, cluster.platform_region, cluster.environment)
        if env is None:
            continue
        if resources:
            ingest_cluster_inventory(repo.session, environment=env, cluster=cluster, resources=resources)
        else:
            ingest_snapshot(repo.session, cluster, snapshot, env)
    for environment in account.environments:
        repo.mark_scope_success(environment_scope_id(account.alias, environment), "health")
    return len(items)


def correlate_changes(session: Session, row: ApplicationHealthRow) -> dict:
    window = utcnow() - timedelta(minutes=settings.health_correlation_window_minutes)
    evidence: dict = {"windowMinutes": settings.health_correlation_window_minutes, "pipelineRuns": [], "certificates": []}
    runs = list(
        session.scalars(
            select(PipelineRunRow)
            .where(PipelineRunRow.application_id.in_((row.application_id, "")))
            .order_by(PipelineRunRow.started_at.desc())
        )
    )
    for run in runs:
        started = _aware(run.started_at or run.updated_at)
        if started and started >= window and (not run.application_id or run.application_id == row.application_id or run.environment_id == row.environment_id):
            evidence["pipelineRuns"].append(
                {
                    "id": run.id,
                    "status": run.status,
                    "commitSha": run.commit_sha,
                    "startedAt": started.isoformat() if started else None,
                    "externalRunId": run.external_run_id,
                }
            )
            add_timeline(
                session,
                application_id=row.application_id,
                environment_id=row.environment_id,
                event_type="pipeline",
                title=f"pipeline {run.status.lower()}",
                detail=run.commit_sha,
                href=f"/pipelines?run={run.id}",
                when=started,
            )
    certs = list(
        session.scalars(
            select(AcmCertificateRow).where(
                AcmCertificateRow.environment == row.environment,
                AcmCertificateRow.platform_region == row.region,
            )
        )
    )
    for cert in certs:
        status = cert.expiry_status or ""
        if status in {EXPIRED, CRITICAL, "EXPIRED"}:
            evidence["certificates"].append({"id": cert.id, "domain": cert.domain_name, "status": status})
    return evidence


def _active_incident(session: Session, application_id: str, environment_id: str) -> HealthIncidentRow | None:
    return session.scalar(
        select(HealthIncidentRow).where(
            HealthIncidentRow.application_id == application_id,
            HealthIncidentRow.environment_id == environment_id,
            HealthIncidentRow.status.in_((INCIDENT_OPEN, INCIDENT_ACKNOWLEDGED)),
        )
    )


def evaluate_incident(session: Session, row: ApplicationHealthRow) -> None:
    failing = row.status in {UNHEALTHY, CRITICAL}
    incident = _active_incident(session, row.application_id, row.environment_id)
    if failing and row.consecutive_unhealthy >= settings.health_incident_open_threshold and incident is None:
        incident = HealthIncidentRow(
            id=_id("inc", row.application_id, row.environment_id, str(utcnow().timestamp())),
            application_id=row.application_id,
            environment_id=row.environment_id,
            provider=row.provider,
            region=row.region,
            environment=row.environment,
            status=INCIDENT_OPEN,
            severity=health_to_alert_severity(row.status),
            root_symptom=row.summary or row.status,
            affected_resources_json=row.evidence_json,
            opened_at=utcnow(),
        )
        session.add(incident)
        add_timeline(
            session,
            application_id=row.application_id,
            environment_id=row.environment_id,
            event_type="incident",
            title="incident opened",
            detail=row.summary,
            href=f"/health-checks?incident={incident.id}",
        )
    elif (not failing) and incident is not None and row.consecutive_healthy >= settings.health_incident_resolve_threshold:
        incident.status = INCIDENT_RESOLVED
        incident.resolved_at = utcnow()
        add_timeline(
            session,
            application_id=row.application_id,
            environment_id=row.environment_id,
            event_type="incident",
            title="incident resolved",
            detail=row.summary,
            href=f"/health-checks?incident={incident.id}",
        )


def upsert_alert(session: Session, *, kind: str, row: ApplicationHealthRow, title: str) -> HealthAlertRow | None:
    if row.status in {HEALTHY, UNKNOWN}:
        return None
    fingerprint = _id("al", kind, row.application_id, row.environment_id)
    existing = session.get(HealthAlertRow, fingerprint)
    if existing is None:
        existing = session.scalar(select(HealthAlertRow).where(HealthAlertRow.fingerprint == fingerprint))
    now = utcnow()
    if existing is not None:
        existing.status = "OPEN"
        existing.resolved_at = None
        existing.last_evaluated_at = now
        existing.title = title
        existing.severity = health_to_alert_severity(row.status)
        return existing
    alert = HealthAlertRow(
        id=fingerprint,
        kind=kind,
        fingerprint=fingerprint,
        application_id=row.application_id,
        environment_id=row.environment_id,
        cluster_id=row.cluster_id,
        environment=row.environment,
        severity=health_to_alert_severity(row.status),
        status="OPEN",
        title=title,
        created_at=now,
        last_evaluated_at=now,
    )
    session.add(alert)
    session.flush()
    return alert


def maybe_notify(session: Session, row: ApplicationHealthRow, kind: str) -> None:
    severity = health_to_alert_severity(row.status)
    if not meets_notification_floor(row.environment, severity):
        return
    from app.db.models import NotificationEventRow

    cutoff = utcnow() - timedelta(seconds=settings.certificate_notification_cooldown_seconds)
    recent = session.scalar(
        select(NotificationEventRow).where(
            NotificationEventRow.certificate_id == row.id,
            NotificationEventRow.event_type == kind,
            NotificationEventRow.created_at >= cutoff,
        )
    )
    if recent is not None:
        return
    provider = get_notification_provider()
    payload = {
        "kind": kind,
        "application": row.application_name or row.application_id,
        "environment": row.environment,
        "region": row.region,
        "provider": row.provider,
        "status": row.status,
        "summary": row.summary,
    }
    provider.send(kind, payload)
    session.add(
        NotificationEventRow(
            id=str(uuid4()),
            certificate_id=row.id,
            event_type=kind,
            channel=provider.name,
            payload=sanitize_text(_json(payload)),
            created_at=utcnow(),
        )
    )


def aggregate_application_row(session: Session, application_id: str, environment: CloudEnvironmentRow) -> ApplicationHealthRow:
    now = utcnow()
    resources = list(
        session.scalars(
            select(ResourceHealthRow).where(
                ResourceHealthRow.application_id == application_id,
                ResourceHealthRow.environment_id == environment.id,
            )
        )
    )
    workloads = [item for item in resources if item.resource_type in {"deployment", "statefulset", "daemonset"}]
    pods = [item for item in resources if item.resource_type == "pod"]
    ingresses = [item for item in resources if item.resource_type == "ingress"]
    endpoints = [item for item in resources if item.resource_type == "http_endpoint"]
    cluster_rows = [item for item in resources if item.resource_type == "cluster"]
    certs = list(
        session.scalars(
            select(AcmCertificateRow).where(
                AcmCertificateRow.environment == environment.environment,
                AcmCertificateRow.platform_region == environment.platform_region,
            )
        )
    )
    cert_status = UNKNOWN
    if certs:
        if any((item.expiry_status or "") in {EXPIRED, "EXPIRED"} for item in certs):
            cert_status = CRITICAL
        elif any((item.expiry_status or "") in {"WARNING", "CRITICAL", "URGENT"} for item in certs):
            cert_status = DEGRADED
        else:
            cert_status = HEALTHY
    latest_run = session.scalar(
        select(PipelineRunRow)
        .where(PipelineRunRow.application_id == application_id)
        .order_by(PipelineRunRow.started_at.desc())
    )
    pipeline_status = latest_run.status if latest_run else UNKNOWN
    signals = HealthSignals(
        workload_status=worst(*(item.status for item in workloads)) if workloads else UNKNOWN,
        desired_replicas=sum(item.desired for item in workloads) or sum(item.desired for item in pods),
        available_replicas=sum(item.available or item.ready for item in workloads) or sum(item.ready for item in pods),
        crashloop=sum(1 for item in pods if item.reason == "CrashLoopBackOff"),
        failed_pods=sum(1 for item in pods if item.status in {UNHEALTHY, CRITICAL}),
        restart_count=sum(item.restart_count for item in pods),
        http_status=worst(*(item.status for item in endpoints)) if endpoints else UNKNOWN,
        ingress_status=worst(*(item.status for item in ingresses)) if ingresses else UNKNOWN,
        certificate_status=cert_status,
        pipeline_status=pipeline_status,
        deployment_status=latest_run.status if latest_run else UNKNOWN,
        cluster_status=worst(*(item.status for item in cluster_rows)) if cluster_rows else UNKNOWN,
        restart_degraded_threshold=settings.health_restart_degraded_threshold,
    )
    result = aggregate_application(signals)
    row_id = _id("ah", application_id, environment.id)
    row = session.get(ApplicationHealthRow, row_id)
    if row is None:
        row = session.scalar(
            select(ApplicationHealthRow).where(
                ApplicationHealthRow.application_id == application_id,
                ApplicationHealthRow.environment_id == environment.id,
            )
        )
    previous = row.status if row else UNKNOWN
    if row is None:
        row = ApplicationHealthRow(
            id=row_id,
            application_id=application_id,
            environment_id=environment.id,
            status=UNKNOWN,
            consecutive_unhealthy=0,
            consecutive_healthy=0,
            updated_at=now,
        )
        session.add(row)
        session.flush()
    named = next(
        (
            item.resource_name
            for item in workloads + pods
            if item.resource_name and not item.resource_name.startswith("_")
        ),
        "",
    )
    row.application_name = named or row.application_name or application_id
    row.provider = environment.provider
    row.region = environment.platform_region
    row.environment = environment.environment
    row.cluster_id = resources[0].cluster_id if resources else row.cluster_id
    row.status = result.status
    row.summary = result.summary
    row.likely_cause = result.likely_cause
    row.evidence_json = _json(result.evidence)
    row.desired_replicas = signals.desired_replicas
    row.available_replicas = signals.available_replicas
    row.crashloop = signals.crashloop
    row.failed_pods = signals.failed_pods
    row.restart_count = signals.restart_count
    row.http_status = signals.http_status
    row.ingress_status = signals.ingress_status
    row.certificate_status = signals.certificate_status
    row.pipeline_status = signals.pipeline_status
    row.deployment_status = signals.deployment_status
    row.cluster_status = signals.cluster_status
    row.last_attempted_at = now
    row.error_category = ""
    if result.status == HEALTHY:
        row.consecutive_healthy = (row.consecutive_healthy or 0) + 1
        row.consecutive_unhealthy = 0
        row.last_successful_at = now
    elif result.status in {UNHEALTHY, CRITICAL}:
        row.consecutive_unhealthy = (row.consecutive_unhealthy or 0) + 1
        row.consecutive_healthy = 0
    row.updated_at = now
    correlation = correlate_changes(session, row)
    if correlation.get("pipelineRuns") and result.status in {UNHEALTHY, CRITICAL, DEGRADED}:
        run = correlation["pipelineRuns"][0]
        ext = run.get("externalRunId") or run.get("id")
        commit = (run.get("commitSha") or "")[:7]
        if "deployment" in (row.likely_cause or "").lower() or not row.likely_cause:
            row.likely_cause = f"Likely related to Deployment #{ext} commit {commit}".strip()
    if correlation.get("certificates") and result.status in {UNHEALTHY, CRITICAL}:
        row.likely_cause = "Likely related to an expired certificate"
    row.correlation_json = _json(correlation)
    session.add(
        HealthCheckResultRow(
            id=str(uuid4()),
            application_id=application_id,
            environment_id=environment.id,
            cluster_id=row.cluster_id,
            check_type="APPLICATION_AGGREGATE",
            status=result.status,
            summary=result.summary,
            created_at=now,
        )
    )
    if previous != result.status:
        add_timeline(
            session,
            application_id=application_id,
            environment_id=environment.id,
            event_type="status",
            title=f"application {result.status.lower()}",
            detail=result.summary,
            href=f"/health-checks?app={application_id}",
        )
    if signals.crashloop and result.status in {UNHEALTHY, CRITICAL}:
        add_timeline(
            session,
            application_id=application_id,
            environment_id=environment.id,
            event_type="pods",
            title="pod restart rate increased",
            detail=f"{signals.crashloop} CrashLoopBackOff",
        )
    evaluate_incident(session, row)
    if result.status == CRITICAL:
        upsert_alert(session, kind="APPLICATION_CRITICAL", row=row, title=f"{row.application_name or application_id} critical")
        maybe_notify(session, row, "APPLICATION_CRITICAL")
    elif result.status == UNHEALTHY:
        upsert_alert(session, kind="APPLICATION_UNHEALTHY", row=row, title=f"{row.application_name or application_id} unhealthy")
        maybe_notify(session, row, "APPLICATION_UNHEALTHY")
    elif result.status == HEALTHY:
        for alert in session.scalars(
            select(HealthAlertRow).where(
                HealthAlertRow.application_id == application_id,
                HealthAlertRow.environment_id == environment.id,
                HealthAlertRow.status == "OPEN",
            )
        ):
            alert.status = "RESOLVED"
            alert.resolved_at = now
            alert.last_evaluated_at = now
    labels = {
        "provider": environment.provider.lower(),
        "region": environment.platform_region.lower(),
        "environment_class": environment_class(environment.environment),
        "health_status": result.status.lower(),
    }
    set_gauge("cloudops_application_health_total", labels, 1)
    return row


def scan_environment_clusters(session: Session, environment: CloudEnvironmentRow, inventories: dict[str, list[NormalizedResource] | Exception] | None = None) -> None:
    repo = InventoryRepository(session)
    clusters = [
        cluster
        for cluster in repo.present_clusters_for(environment.platform_region, environment.environment)
        if cluster.provider == environment.provider
    ]
    now = utcnow()
    environment.last_attempted_scan_at = now
    if inventories is not None and environment.id in inventories:
        payload = inventories[environment.id]
        if isinstance(payload, Exception):
            environment.last_error = sanitize_text(str(payload))[:500]
            environment.last_error_class = payload.__class__.__name__
            environment.last_error_at = now
            inc(
                "cloudops_health_check_failures_total",
                {
                    "provider": environment.provider.lower(),
                    "region": environment.platform_region.lower(),
                    "environment_class": environment_class(environment.environment),
                    "health_status": "failed",
                },
            )
            return
        if not clusters:
            # Persist inventory against a synthetic cluster id for tests without live discovery.
            synthetic = EksClusterRow(
                id=_id("cl", environment.id),
                arn=f"arn:test:{environment.id}",
                name=f"{environment.environment}-cluster",
                cloud_region=environment.cloud_region,
                aws_account_id="",
                account_alias=environment.account_alias,
                provider=environment.provider,
                platform_region=environment.platform_region,
                environment=environment.environment,
            )
            ingest_cluster_inventory(session, environment=environment, cluster=synthetic, resources=payload)
            if not environment.last_error:
                environment.last_successful_scan_at = now
            return
        ingest_cluster_inventory(session, environment=environment, cluster=clusters[0], resources=payload)
        if not environment.last_error:
            environment.last_successful_scan_at = now
        return
    for cluster in clusters:
        snapshot_row = session.get(EksClusterHealthRow, cluster.id)
        if snapshot_row is None:
            continue
        ingest_snapshot(session, cluster, snapshot_row, environment)
    if not environment.last_error:
        environment.last_successful_scan_at = now


def run_isolated(session: Session, environments: list[CloudEnvironmentRow], worker) -> int:
    processed = 0
    for environment in environments:
        if not acquire_lock(session, environment.id, owner=worker.__name__ if hasattr(worker, "__name__") else "scan"):
            continue
        try:
            worker(session, environment)
            lock = session.get(HealthScanLockRow, environment.id)
            if lock is not None:
                session.delete(lock)
            session.commit()
            processed += 1
        except Exception as error:
            session.rollback()
            logger.warning("Health scan isolated failure environment=%s error=%s", environment.id, error)
            env = session.get(CloudEnvironmentRow, environment.id)
            if env is not None:
                env.last_attempted_scan_at = utcnow()
                env.last_error = sanitize_text(str(error))[:500]
                env.last_error_class = error.__class__.__name__
                env.last_error_at = utcnow()
                lock = session.get(HealthScanLockRow, environment.id)
                if lock is not None:
                    session.delete(lock)
                session.commit()
            inc(
                "cloudops_health_check_failures_total",
                {
                    "provider": environment.provider.lower(),
                    "region": environment.platform_region.lower(),
                    "environment_class": environment_class(environment.environment),
                    "health_status": "failed",
                },
            )
    return processed


def run_cluster_health_scan(job_id: str, inventories: dict | None = None) -> int:
    started = utcnow()
    session = SessionLocal()
    try:
        _mark_running(session, job_id)
        environments = list(session.scalars(select(CloudEnvironmentRow)))
        count = run_isolated(
            session,
            environments,
            lambda sess, env: scan_environment_clusters(sess, env, inventories),
        )
        _finish(session, job_id, f"cluster-health-scan:{count}")
        observe_duration(
            "cloudops_health_scan_duration_seconds",
            {"provider": "all", "region": "all", "environment_class": "all", "health_status": "ok"},
            (utcnow() - started).total_seconds(),
        )
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_application_health_scan(job_id: str) -> int:
    started = utcnow()
    session = SessionLocal()
    try:
        _mark_running(session, job_id)

        def worker(sess: Session, environment: CloudEnvironmentRow) -> None:
            app_ids = {
                item.application_id
                for item in sess.scalars(
                    select(ResourceHealthRow).where(ResourceHealthRow.environment_id == environment.id)
                )
                if item.application_id
            }
            app_ids.update(
                item.application_id
                for item in sess.scalars(
                    select(ApplicationResourceMappingRow).where(
                        ApplicationResourceMappingRow.environment_id.in_((environment.id, "")),
                        ApplicationResourceMappingRow.active.is_(True),
                    )
                )
            )
            for application_id in app_ids:
                aggregate_application_row(sess, application_id, environment)

        count = run_isolated(session, list(session.scalars(select(CloudEnvironmentRow))), worker)
        _refresh_gauges(session)
        _finish(session, job_id, f"application-health-scan:{count}")
        observe_duration(
            "cloudops_health_scan_duration_seconds",
            {"provider": "all", "region": "all", "environment_class": "all", "health_status": "ok"},
            (utcnow() - started).total_seconds(),
        )
        return count
    finally:
        session.close()


def run_http_health_check(job_id: str) -> int:
    session = SessionLocal()
    try:
        _mark_running(session, job_id)
        job = session.get(PlatformJobRow, job_id)
        target = job.target_id if job else ""
        query = select(HealthCheckDefinitionRow).where(
            HealthCheckDefinitionRow.enabled.is_(True),
            HealthCheckDefinitionRow.check_type.in_(("HTTP_ENDPOINT", "DEPENDENCY_HTTP", "INGRESS_REACHABILITY")),
        )
        if target:
            query = select(HealthCheckDefinitionRow).where(HealthCheckDefinitionRow.id == target)
        checked = 0
        for definition in session.scalars(query):
            definition.last_attempted_at = utcnow()
            if not definition.url:
                continue
            env = session.get(CloudEnvironmentRow, definition.environment_id) if definition.environment_id else None
            try:
                result = probe_http(
                    definition.url,
                    method=definition.method,
                    timeout=definition.timeout_seconds,
                    expected=definition.expected_status,
                    expected_pattern=definition.expected_pattern,
                    registered=True,
                )
                definition.last_error_category = result.error_category
                if result.success:
                    definition.last_successful_at = utcnow()
                session.add(
                    HealthCheckResultRow(
                        id=str(uuid4()),
                        definition_id=definition.id,
                        application_id=definition.application_id,
                        environment_id=definition.environment_id,
                        cluster_id=definition.cluster_id,
                        check_type=definition.check_type,
                        status=result.status,
                        latency_ms=result.latency_ms,
                        status_code=result.status_code,
                        summary=result.summary,
                        error_category=result.error_category,
                        created_at=utcnow(),
                    )
                )
                if env is not None and definition.application_id:
                    persist_resources(
                        session,
                        [
                            NormalizedResource(
                                resource_type="http_endpoint",
                                name=definition.name,
                                status=result.status,
                                summary=result.summary,
                                check_type="HTTP_ENDPOINT",
                                error_category=result.error_category,
                            )
                        ],
                        cluster_id=definition.cluster_id,
                        environment=env,
                        application_id=definition.application_id,
                        definition_id=definition.id,
                        prune_stale=False,
                    )
                if result.status in {UNHEALTHY, CRITICAL} and definition.application_id:
                    app_row = session.scalar(
                        select(ApplicationHealthRow).where(
                            ApplicationHealthRow.application_id == definition.application_id,
                            ApplicationHealthRow.environment_id == definition.environment_id,
                        )
                    )
                    if app_row is not None:
                        upsert_alert(session, kind="ENDPOINT_UNAVAILABLE", row=app_row, title=f"{definition.name} unavailable")
                        maybe_notify(session, app_row, "ENDPOINT_UNAVAILABLE")
                        add_timeline(
                            session,
                            application_id=definition.application_id,
                            environment_id=definition.environment_id,
                            event_type="http",
                            title="HTTP health failed",
                            detail=result.summary,
                        )
                inc(
                    "cloudops_health_checks_total",
                    {
                        "provider": (env.provider if env else "aws").lower(),
                        "region": (env.platform_region if env else "emea").lower(),
                        "environment_class": environment_class(env.environment if env else ""),
                        "health_status": result.status.lower(),
                    },
                )
                if not result.success:
                    inc(
                        "cloudops_health_check_failures_total",
                        {
                            "provider": (env.provider if env else "aws").lower(),
                            "region": (env.platform_region if env else "emea").lower(),
                            "environment_class": environment_class(env.environment if env else ""),
                            "health_status": "failed",
                        },
                    )
                checked += 1
            except EndpointPolicyError as error:
                definition.last_error_category = "ssrf"
                session.add(
                    HealthCheckResultRow(
                        id=str(uuid4()),
                        definition_id=definition.id,
                        application_id=definition.application_id,
                        environment_id=definition.environment_id,
                        check_type=definition.check_type,
                        status=CRITICAL,
                        summary=str(error),
                        error_category="ssrf",
                        created_at=utcnow(),
                    )
                )
                checked += 1
        _finish(session, job_id, f"http-health-check:{checked}")
        return checked
    finally:
        session.close()


def run_dependency_health_check(job_id: str) -> int:
    session = SessionLocal()
    try:
        _mark_running(session, job_id)
        checked = 0
        for dependency in session.scalars(select(ApplicationDependencyRow)):
            definition = session.get(HealthCheckDefinitionRow, dependency.health_check_definition_id) if dependency.health_check_definition_id else None
            status = UNKNOWN
            summary = f"{dependency.dependency_type} {dependency.external_name or dependency.target_application_id}"
            if dependency.dependency_type == "APPLICATION" and dependency.target_application_id:
                target = session.scalar(
                    select(ApplicationHealthRow).where(ApplicationHealthRow.application_id == dependency.target_application_id)
                )
                status = target.status if target else UNKNOWN
                summary = f"dependency {dependency.target_application_id} {status}"
            elif definition and definition.url:
                try:
                    result = probe_http(definition.url, method=definition.method, timeout=definition.timeout_seconds, expected=definition.expected_status, registered=True)
                    status = result.status
                    summary = result.summary
                except EndpointPolicyError as error:
                    status = CRITICAL
                    summary = str(error)
            elif dependency.dependency_type in {"DATABASE", "REDIS", "RABBITMQ"}:
                # Connectivity uses credential references only; live sockets are optional.
                status = HEALTHY if dependency.credential_ref else UNKNOWN
                summary = "credential reference present" if dependency.credential_ref else "insufficient data"
            session.add(
                HealthCheckResultRow(
                    id=str(uuid4()),
                    definition_id=dependency.health_check_definition_id,
                    application_id=dependency.source_application_id,
                    check_type=f"{dependency.dependency_type}_CONNECTIVITY" if dependency.dependency_type != "HTTP" else "DEPENDENCY_HTTP",
                    status=status,
                    summary=summary[:512],
                    created_at=utcnow(),
                )
            )
            checked += 1
        _finish(session, job_id, f"dependency-health-check:{checked}")
        return checked
    finally:
        session.close()


def run_health_aggregation(job_id: str) -> int:
    return run_application_health_scan(job_id)


def run_health_alert_evaluation(job_id: str) -> int:
    session = SessionLocal()
    try:
        _mark_running(session, job_id)
        evaluated = 0
        for row in session.scalars(select(ApplicationHealthRow)):
            if row.status == CRITICAL:
                upsert_alert(session, kind="APPLICATION_CRITICAL", row=row, title=f"{row.application_name or row.application_id} critical")
            elif row.status == UNHEALTHY:
                upsert_alert(session, kind="APPLICATION_UNHEALTHY", row=row, title=f"{row.application_name or row.application_id} unhealthy")
            if row.cluster_status in {UNHEALTHY, CRITICAL}:
                upsert_alert(session, kind="CLUSTER_UNHEALTHY", row=row, title=f"cluster unhealthy ({row.environment})")
            if row.desired_replicas and row.available_replicas == 0:
                upsert_alert(session, kind="WORKLOAD_UNAVAILABLE", row=row, title=f"{row.application_name or row.application_id} workload unavailable")
            evaluated += 1
        for cluster in session.scalars(select(ResourceHealthRow).where(ResourceHealthRow.resource_type == "cluster")):
            labels = {
                "provider": cluster.provider.lower() or "aws",
                "region": cluster.region.lower() or "emea",
                "environment_class": environment_class(cluster.environment),
                "health_status": cluster.status.lower(),
            }
            set_gauge("cloudops_cluster_health_total", labels, 1)
        open_incidents = session.scalars(select(HealthIncidentRow).where(HealthIncidentRow.status.in_((INCIDENT_OPEN, INCIDENT_ACKNOWLEDGED)))).all()
        by_scope: dict[tuple[str, str, str], int] = {}
        for incident in open_incidents:
            key = (incident.provider.lower() or "aws", incident.region.lower() or "emea", environment_class(incident.environment))
            by_scope[key] = by_scope.get(key, 0) + 1
        for (provider, region, klass), total in by_scope.items():
            set_gauge(
                "cloudops_open_incidents_total",
                {"provider": provider, "region": region, "environment_class": klass, "health_status": "open"},
                total,
            )
        _finish(session, job_id, f"health-alert-evaluation:{evaluated}")
        return evaluated
    finally:
        session.close()


def run_health_retention(job_id: str) -> int:
    session = SessionLocal()
    try:
        _mark_running(session, job_id)
        now = utcnow()
        detailed_cutoff = now - timedelta(days=settings.health_result_retention_days)
        aggregate_cutoff = now - timedelta(days=settings.health_aggregate_retention_days)
        detailed = session.execute(
            delete(HealthCheckResultRow).where(
                HealthCheckResultRow.created_at < detailed_cutoff,
                HealthCheckResultRow.check_type != "APPLICATION_AGGREGATE",
            )
        )
        aggregated = session.execute(
            delete(HealthCheckResultRow).where(
                HealthCheckResultRow.created_at < aggregate_cutoff,
                HealthCheckResultRow.check_type == "APPLICATION_AGGREGATE",
            )
        )
        timeline = session.execute(delete(HealthTimelineEventRow).where(HealthTimelineEventRow.created_at < aggregate_cutoff))
        removed = (detailed.rowcount or 0) + (aggregated.rowcount or 0) + (timeline.rowcount or 0)
        _finish(session, job_id, f"health-retention:{removed}")
        return removed
    finally:
        session.close()


def acknowledge_incident(session: Session, incident_id: str, actor: str) -> HealthIncidentRow | None:
    incident = session.get(HealthIncidentRow, incident_id)
    if incident is None:
        return None
    incident.status = INCIDENT_ACKNOWLEDGED
    incident.acknowledged_at = utcnow()
    incident.acknowledged_by = actor
    record_audit(session, "INCIDENT_ACKNOWLEDGED", actor=actor, object_name=incident_id, detail=incident.root_symptom)
    return incident


def _refresh_gauges(session: Session) -> None:
    counts: dict[tuple[str, str, str, str], int] = {}
    for row in session.scalars(select(ApplicationHealthRow)):
        key = (row.provider.lower() or "aws", row.region.lower() or "emea", environment_class(row.environment), row.status.lower())
        counts[key] = counts.get(key, 0) + 1
    for (provider, region, klass, status), total in counts.items():
        set_gauge(
            "cloudops_application_health_total",
            {"provider": provider, "region": region, "environment_class": klass, "health_status": status},
            total,
        )


def _mark_running(session: Session, job_id: str) -> None:
    InventoryRepository(session).mark_job_running(job_id)
    session.commit()


def _finish(session: Session, job_id: str, detail: str) -> None:
    InventoryRepository(session).mark_job_finished(job_id, status="succeeded", detail=detail)
    session.commit()
