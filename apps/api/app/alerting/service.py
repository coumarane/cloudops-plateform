from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting.deduplication import fingerprint
from app.alerting.escalation import due_for_escalation, due_for_repeat
from app.alerting.exceptions import AlertNotFoundError, AlertStateError
from app.alerting.models import (
    ACTIVE_STATUSES,
    AlertSignal,
    AlertStatus,
    DeliveryStatus,
    NotificationType,
    normalize_severity,
)
from app.alerting.repositories import (
    active_by_fingerprint,
    latest_by_fingerprint,
    list_destinations,
    list_policies,
    list_routes,
    list_rules,
    policy_steps,
)
from app.alerting.routing import matching_routes
from app.alerting.rules import rule_allows_notification, select_rule
from app.alerting.suppression import active_maintenance, active_suppression, expire_maintenance_windows, expire_suppressions
from app.core.logging import get_logger, sanitize_text
from app.core.metrics import inc, set_gauge
from app.db.models import (
    AlertAuditRow,
    AlertEventRow,
    AlertRow,
    AlertRuleRow,
    AlertRoutingRuleRow,
    AlertSuppressionRow,
    MaintenanceWindowRow,
    NotificationDeliveryRow,
    NotificationDestinationRow,
    NotificationPolicyRow,
    NotificationPolicyStepRow,
)
from app.db.repository import utcnow
from app.notifications.dispatcher import dispatch_pending

logger = get_logger(__name__)


def _id(*parts: str) -> str:
    from hashlib import sha256

    return sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def _event(session: Session, alert_id: str, event_type: str, title: str, detail: str = "", actor: str = "system") -> None:
    session.add(
        AlertEventRow(
            id=str(uuid4()),
            alert_id=alert_id,
            event_type=event_type,
            title=title,
            detail=sanitize_text(detail)[:512],
            actor=actor,
            created_at=utcnow(),
        )
    )


def record_audit(session: Session, action: str, *, actor: str, object_name: str = "", detail: str = "") -> None:
    session.add(
        AlertAuditRow(
            id=str(uuid4()),
            action=action,
            actor=actor,
            object_name=object_name,
            result="succeeded",
            detail=sanitize_text(detail)[:2000],
            created_at=utcnow(),
        )
    )


def ensure_defaults(session: Session) -> None:
    now = utcnow()
    destinations = {
        "dest-log-ops": ("Operations Log", "log", "Default local operations sink"),
        "dest-email-oncall": ("On-Call Email", "email", "On-call mailbox"),
        "dest-teams-critical": ("CloudOps Critical Teams", "teams", "PRD critical Teams channel"),
        "dest-slack-emea": ("EMEA DevOps Slack", "slack", "EMEA operations channel"),
        "dest-webhook-china": ("China Operations Webhook", "webhook", "Alibaba China operations"),
        "dest-webhook-mgmt": ("Management escalation webhook", "webhook", "Escalation destination"),
        "dest-log-payments": ("Payments team", "log", "Payments application owners"),
    }
    for dest_id, (name, provider, description) in destinations.items():
        if session.get(NotificationDestinationRow, dest_id) is None:
            extra = {"to": "oncall@cloudops.local"} if provider == "email" else {}
            session.add(
                NotificationDestinationRow(
                    id=dest_id,
                    name=name,
                    provider_type=provider,
                    configuration_reference="",
                    config_json=json.dumps(extra),
                    enabled=True,
                    description=description,
                    created_at=now,
                    updated_at=now,
                )
            )
    policies = {
        "policy-default": ("Default", True, 0, 0, True),
        "policy-prd-critical": ("PRD Critical", True, 0, 1800, True),
        "policy-uat": ("UAT Medium+", True, 0, 0, True),
    }
    for policy_id, (name, initial, repeat, escalate, recovery) in policies.items():
        if session.get(NotificationPolicyRow, policy_id) is None:
            session.add(
                NotificationPolicyRow(
                    id=policy_id,
                    name=name,
                    initial_enabled=initial,
                    repeat_after_seconds=repeat,
                    escalate_after_seconds=escalate,
                    recovery_enabled=recovery,
                    created_at=now,
                    updated_at=now,
                )
            )
    steps = [
        ("step-default-initial", "policy-default", 0, "dest-log-ops", NotificationType.INITIAL),
        ("step-prd-teams", "policy-prd-critical", 0, "dest-teams-critical", NotificationType.INITIAL),
        ("step-prd-email", "policy-prd-critical", 600, "dest-email-oncall", NotificationType.ESCALATION),
        ("step-prd-mgmt", "policy-prd-critical", 1800, "dest-webhook-mgmt", NotificationType.ESCALATION),
        ("step-prd-recovery", "policy-prd-critical", 0, "dest-teams-critical", NotificationType.RECOVERY),
        ("step-uat-initial", "policy-uat", 0, "dest-log-ops", NotificationType.INITIAL),
    ]
    for step_id, policy_id, delay, dest, step_type in steps:
        if session.get(NotificationPolicyStepRow, step_id) is None:
            session.add(
                NotificationPolicyStepRow(
                    id=step_id,
                    policy_id=policy_id,
                    delay_seconds=delay,
                    destination_id=dest,
                    step_type=step_type,
                    enabled=True,
                )
            )
    env_rules = [
        ("rule-dev", "DEV disabled", "DEV", "CRITICAL", False, "policy-default"),
        ("rule-tst", "TST LOW", "INT/TST", "LOW", True, "policy-default"),
        ("rule-uat", "UAT MEDIUM", "UAT", "MEDIUM", True, "policy-uat"),
        ("rule-npd", "NPD HIGH", "NPD", "HIGH", True, "policy-default"),
        ("rule-prd", "PRD CRITICAL", "PRD", "CRITICAL", True, "policy-prd-critical"),
    ]
    for rule_id, name, environment, severity, enabled, policy_id in env_rules:
        if session.get(AlertRuleRow, rule_id) is None:
            session.add(
                AlertRuleRow(
                    id=rule_id,
                    name=name,
                    alert_type="",
                    enabled=enabled,
                    environment_filter=environment,
                    severity=severity,
                    minimum_occurrences=1,
                    notification_policy_id=policy_id,
                    created_at=now,
                    updated_at=now,
                )
            )
    routes = [
        ("route-prd-critical", "PRD CRITICAL", "PRD", "CRITICAL", "", "", "", "dest-teams-critical", "policy-prd-critical"),
        ("route-emea", "AWS EMEA", "", "", "AWS", "EMEA", "", "dest-slack-emea", "policy-default"),
        ("route-china", "Alibaba China", "", "", "Alibaba", "China", "", "dest-webhook-china", "policy-default"),
        ("route-payments", "Payments team", "", "", "", "", "payments-api", "dest-log-payments", "policy-default"),
    ]
    for route_id, name, environment, severity, provider, region, application, dest, policy_id in routes:
        if session.get(AlertRoutingRuleRow, route_id) is None:
            session.add(
                AlertRoutingRuleRow(
                    id=route_id,
                    name=name,
                    enabled=True,
                    provider_filter=provider,
                    region_filter=region,
                    environment_filter=environment,
                    application_filter=application,
                    severity_filter=severity,
                    destination_id=dest,
                    policy_id=policy_id,
                    created_at=now,
                )
            )
    session.flush()


def _signal_from_alert(alert: AlertRow) -> AlertSignal:
    return AlertSignal(
        alert_type=alert.alert_type,
        source_type=alert.source_type,
        source_id=alert.source_id,
        title=alert.title,
        summary=alert.summary,
        severity=alert.severity,
        provider=alert.provider,
        region=alert.region,
        account_id=alert.account_id,
        environment_id=alert.environment_id,
        environment=alert.environment,
        application_id=alert.application_id,
        cluster_id=alert.cluster_id,
        correlation_id=alert.correlation_id,
    )


def _queue_deliveries(
    session: Session,
    alert: AlertRow,
    signal: AlertSignal,
    *,
    notification_type: str,
    destinations: list[str],
) -> None:
    for dest_id in destinations:
        if not dest_id:
            continue
        existing = session.scalar(
            select(NotificationDeliveryRow).where(
                NotificationDeliveryRow.alert_id == alert.id,
                NotificationDeliveryRow.destination_id == dest_id,
                NotificationDeliveryRow.notification_type == notification_type,
                NotificationDeliveryRow.status.in_((DeliveryStatus.SENT, DeliveryStatus.PENDING, DeliveryStatus.RETRY)),
            )
        )
        if existing is not None and notification_type != NotificationType.REPEAT:
            continue
        session.add(
            NotificationDeliveryRow(
                id=str(uuid4()),
                alert_id=alert.id,
                destination_id=dest_id,
                notification_type=notification_type,
                status=DeliveryStatus.PENDING,
                attempt=0,
            )
        )


def _destination_ids(session: Session, signal: AlertSignal, alert: AlertRow, step_type: str) -> list[str]:
    ids: list[str] = []
    for route in matching_routes(list_routes(session), signal):
        if route.destination_id:
            ids.append(route.destination_id)
        if route.policy_id and not alert.policy_id:
            alert.policy_id = route.policy_id
    policy_id = alert.policy_id
    if policy_id:
        for step in policy_steps(session, policy_id, step_type):
            if step.enabled and step.destination_id:
                ids.append(step.destination_id)
    seen: list[str] = []
    for item in ids:
        if item not in seen:
            seen.append(item)
    return seen


def publish(session: Session, signal: AlertSignal) -> AlertRow | None:
    """Ingest a module signal. Never raises on notification failure."""
    ensure_defaults(session)
    signal.severity = normalize_severity(signal.severity)
    fp = fingerprint(signal)
    now = utcnow()
    if signal.recovered:
        return resolve_fingerprint(session, fp, reason=signal.resolution_reason or "source recovered", actor="system")

    alert = active_by_fingerprint(session, fp)
    created = False
    if alert is None:
        previous = latest_by_fingerprint(session, fp)
        if previous is not None and previous.status == AlertStatus.RESOLVED:
            alert = previous
            alert.status = AlertStatus.OPEN
            alert.resolved_at = None
            alert.resolution_reason = ""
            alert.acknowledged_at = None
            alert.acknowledged_by = ""
            alert.acknowledged_comment = ""
            created = True
        else:
            alert = AlertRow(
                id=str(uuid4()),
                fingerprint=fp,
                first_seen_at=now,
                occurrence_count=0,
                status=AlertStatus.OPEN,
            )
            session.add(alert)
            created = True
    else:
        alert.occurrence_count = (alert.occurrence_count or 1) + 1
        alert.last_seen_at = now
        alert.title = signal.title or alert.title
        alert.summary = sanitize_text(signal.summary)[:512] or alert.summary
        alert.severity = signal.severity
        alert.extra_json = json.dumps(signal.metadata or {})
        if alert.status == AlertStatus.SUPPRESSED:
            session.flush()
            return alert
        _event(session, alert.id, "occurrence", f"occurrence #{alert.occurrence_count}", signal.summary)
        session.flush()
        return alert

    alert.alert_type = signal.alert_type
    alert.source_type = signal.source_type
    alert.source_id = signal.source_id
    alert.provider = signal.provider
    alert.region = signal.region
    alert.account_id = signal.account_id
    alert.environment_id = signal.environment_id
    alert.environment = signal.environment
    alert.application_id = signal.application_id
    alert.cluster_id = signal.cluster_id
    alert.severity = signal.severity
    alert.title = signal.title
    alert.summary = sanitize_text(signal.summary)[:512]
    alert.fingerprint = fp
    alert.last_seen_at = now
    alert.occurrence_count = max(alert.occurrence_count, 1)
    alert.correlation_id = signal.correlation_id
    alert.extra_json = json.dumps(signal.metadata or {})
    if created and alert.first_seen_at is None:
        alert.first_seen_at = now

    rule = select_rule(list_rules(session), signal)
    if rule is not None:
        alert.rule_id = rule.id
        alert.policy_id = rule.notification_policy_id or alert.policy_id
        if rule.severity and not signal.severity:
            alert.severity = normalize_severity(rule.severity)
    suppression = active_suppression(session, signal, now=now)
    maintenance = active_maintenance(session, signal, now=now)
    if suppression is not None:
        alert.status = AlertStatus.SUPPRESSED
    session.flush()
    if created:
        inc("cloudops_alerts_created_total", _labels(alert))
        _event(session, alert.id, "opened", "alert opened", signal.summary)
    _refresh_gauges(session)

    if suppression is not None or maintenance is not None:
        _event(session, alert.id, "suppressed" if suppression else "maintenance", "notifications suppressed")
        return alert
    if not rule_allows_notification(rule, signal, alert.occurrence_count):
        return alert
    destinations = _destination_ids(session, signal, alert, NotificationType.INITIAL)
    try:
        _queue_deliveries(session, alert, signal, notification_type=NotificationType.INITIAL, destinations=destinations)
        session.flush()
        dispatch_pending(session, alert_id=alert.id)
    except Exception as error:
        logger.warning("Notification dispatch isolated alert=%s error=%s", alert.id, error)
    return alert


def resolve_fingerprint(session: Session, fp: str, *, reason: str, actor: str = "system") -> AlertRow | None:
    alert = active_by_fingerprint(session, fp)
    if alert is None:
        return None
    return resolve_alert(session, alert.id, reason=reason, actor=actor, manual=False)


def resolve_alert(session: Session, alert_id: str, *, reason: str, actor: str, manual: bool = True) -> AlertRow:
    alert = session.get(AlertRow, alert_id)
    if alert is None:
        raise AlertNotFoundError(alert_id)
    if alert.status == AlertStatus.RESOLVED:
        return alert
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = utcnow()
    alert.resolution_reason = sanitize_text(reason)[:255]
    _event(session, alert.id, "resolved", "alert resolved", reason, actor=actor)
    inc("cloudops_alerts_resolved_total", _labels(alert))
    if manual:
        record_audit(session, "ALERT_MANUALLY_RESOLVED", actor=actor, object_name=alert.title, detail=reason)
    policy = session.get(NotificationPolicyRow, alert.policy_id) if alert.policy_id else None
    if policy is not None and policy.recovery_enabled:
        signal = _signal_from_alert(alert)
        destinations = _destination_ids(session, signal, alert, NotificationType.RECOVERY)
        if not destinations:
            destinations = _destination_ids(session, signal, alert, NotificationType.INITIAL)
        try:
            _queue_deliveries(session, alert, signal, notification_type=NotificationType.RECOVERY, destinations=destinations)
            session.flush()
            dispatch_pending(session, alert_id=alert.id)
        except Exception as error:
            logger.warning("Recovery notification isolated alert=%s error=%s", alert.id, error)
    _refresh_gauges(session)
    return alert


def acknowledge_alert(session: Session, alert_id: str, *, actor: str, comment: str) -> AlertRow:
    alert = session.get(AlertRow, alert_id)
    if alert is None:
        raise AlertNotFoundError(alert_id)
    if alert.status == AlertStatus.RESOLVED:
        raise AlertStateError("resolved alerts cannot be acknowledged")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = utcnow()
    alert.acknowledged_by = actor
    alert.acknowledged_comment = sanitize_text(comment)[:2000]
    _event(session, alert.id, "acknowledged", f"acknowledged by {actor}", comment, actor=actor)
    record_audit(session, "ALERT_ACKNOWLEDGED", actor=actor, object_name=alert.title, detail=comment)
    return alert


def suppress_alert(session: Session, alert_id: str, *, actor: str, reason: str, minutes: int = 60) -> AlertRow:
    from datetime import timedelta

    alert = session.get(AlertRow, alert_id)
    if alert is None:
        raise AlertNotFoundError(alert_id)
    now = utcnow()
    session.add(
        AlertSuppressionRow(
            id=str(uuid4()),
            scope_type="alert",
            scope_id=alert.source_id,
            alert_type=alert.alert_type,
            reason=sanitize_text(reason)[:255],
            starts_at=now,
            ends_at=now + timedelta(minutes=max(minutes, 1)),
            created_by=actor,
            enabled=True,
        )
    )
    alert.status = AlertStatus.SUPPRESSED
    _event(session, alert.id, "suppressed", "alert suppressed", reason, actor=actor)
    record_audit(session, "ALERT_SUPPRESSED", actor=actor, object_name=alert.title, detail=reason)
    return alert


def _labels(alert: AlertRow) -> dict[str, str]:
    env = (alert.environment or "unknown").upper()
    klass = "INT/TST" if env in {"INT/TST", "INT-TST", "INT", "TST"} else env
    return {
        "severity": (alert.severity or "unknown").lower(),
        "provider": (alert.provider or "unknown").lower(),
        "environment_class": klass.lower(),
        "notification_provider": "none",
    }


def _refresh_gauges(session: Session) -> None:
    counts: dict[tuple[str, str, str], int] = {}
    for alert in session.scalars(select(AlertRow).where(AlertRow.status.in_((AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)))):
        key = ((alert.severity or "").lower(), (alert.provider or "unknown").lower(), (alert.environment or "unknown").lower())
        counts[key] = counts.get(key, 0) + 1
    for (severity, provider, env), value in counts.items():
        set_gauge(
            "cloudops_alerts_open_total",
            {"severity": severity, "provider": provider, "environment_class": env, "notification_provider": "none"},
            value,
        )


def run_escalation(session: Session) -> int:
    ensure_defaults(session)
    processed = 0
    now = utcnow()
    for alert, policy, destinations in due_for_escalation(session, now=now):
        signal = _signal_from_alert(alert)
        if alert.status != AlertStatus.OPEN or alert.acknowledged_at is not None or alert.resolved_at is not None:
            continue
        if active_suppression(session, signal, now=now) or active_maintenance(session, signal, now=now):
            continue
        _queue_deliveries(session, alert, signal, notification_type=NotificationType.ESCALATION, destinations=destinations)
        processed += 1
        _event(session, alert.id, "escalation", "escalation queued", policy.name)
    for alert, policy in due_for_repeat(session, now=now):
        if alert.status != AlertStatus.OPEN:
            continue
        signal = _signal_from_alert(alert)
        destinations = _destination_ids(session, signal, alert, NotificationType.INITIAL)
        _queue_deliveries(session, alert, signal, notification_type=NotificationType.REPEAT, destinations=destinations)
        processed += 1
    session.flush()
    try:
        dispatch_pending(session)
    except Exception as error:
        logger.warning("Escalation dispatch isolated error=%s", error)
    return processed


def run_suppression_expiry(session: Session) -> int:
    changed = expire_suppressions(session)
    now = utcnow()
    for alert in session.scalars(select(AlertRow).where(AlertRow.status == AlertStatus.SUPPRESSED)):
        if active_suppression(session, _signal_from_alert(alert), now=now) is None:
            alert.status = AlertStatus.OPEN
            _event(session, alert.id, "suppression_expired", "suppression expired")
            changed += 1
    session.flush()
    return changed


def run_maintenance_expiry(session: Session) -> int:
    return expire_maintenance_windows(session)


def run_recovery_notification(session: Session) -> int:
    return dispatch_pending(session)


def run_alert_evaluate(session: Session) -> int:
    ensure_defaults(session)
    expire_suppressions(session)
    expire_maintenance_windows(session)
    dispatched = dispatch_pending(session)
    escalated = run_escalation(session)
    _refresh_gauges(session)
    return dispatched + escalated


def resolve_source(
    session: Session,
    *,
    source_type: str = "",
    source_id: str = "",
    application_id: str = "",
    environment_id: str = "",
    alert_type: str = "",
    reason: str,
    actor: str = "system",
) -> int:
    query = select(AlertRow).where(AlertRow.status.in_(ACTIVE_STATUSES))
    if source_type:
        query = query.where(AlertRow.source_type == source_type)
    if source_id:
        query = query.where(AlertRow.source_id == source_id)
    if application_id:
        query = query.where(AlertRow.application_id == application_id)
    if environment_id:
        query = query.where(AlertRow.environment_id == environment_id)
    if alert_type:
        query = query.where(AlertRow.alert_type == alert_type)
    resolved = 0
    for alert in list(session.scalars(query)):
        resolve_alert(session, alert.id, reason=reason, actor=actor, manual=False)
        resolved += 1
    return resolved
