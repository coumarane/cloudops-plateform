from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting.models import ACTIVE_STATUSES, AlertStatus, DeliveryStatus, NotificationType
from app.db.models import AlertRow, NotificationDeliveryRow, NotificationPolicyRow, NotificationPolicyStepRow
from app.db.repository import utcnow


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def due_for_escalation(session: Session, *, now=None) -> list[tuple[AlertRow, NotificationPolicyRow, list[str]]]:
    current = now or utcnow()
    policies = {row.id: row for row in session.scalars(select(NotificationPolicyRow))}
    steps_by_policy: dict[str, list[NotificationPolicyStepRow]] = {}
    for step in session.scalars(
        select(NotificationPolicyStepRow).where(NotificationPolicyStepRow.step_type == NotificationType.ESCALATION)
    ):
        steps_by_policy.setdefault(step.policy_id, []).append(step)
    due: list[tuple[AlertRow, NotificationPolicyRow, list[str]]] = []
    for alert in session.scalars(select(AlertRow).where(AlertRow.status == AlertStatus.OPEN)):
        policy = policies.get(alert.policy_id)
        if policy is None:
            continue
        if alert.acknowledged_at is not None or alert.resolved_at is not None:
            continue
        elapsed = (_aware(current) - _aware(alert.first_seen_at)).total_seconds()
        destinations: list[str] = []
        for step in steps_by_policy.get(policy.id, []):
            if not step.enabled or not step.destination_id:
                continue
            delay = step.delay_seconds or policy.escalate_after_seconds
            if elapsed < delay:
                continue
            existing = session.scalar(
                select(NotificationDeliveryRow).where(
                    NotificationDeliveryRow.alert_id == alert.id,
                    NotificationDeliveryRow.destination_id == step.destination_id,
                    NotificationDeliveryRow.notification_type == NotificationType.ESCALATION,
                    NotificationDeliveryRow.status.in_((DeliveryStatus.SENT, DeliveryStatus.PENDING, DeliveryStatus.RETRY)),
                )
            )
            if existing is not None:
                continue
            destinations.append(step.destination_id)
        if not destinations and policy.escalate_after_seconds and elapsed >= policy.escalate_after_seconds:
            existing = session.scalar(
                select(NotificationDeliveryRow).where(
                    NotificationDeliveryRow.alert_id == alert.id,
                    NotificationDeliveryRow.notification_type == NotificationType.ESCALATION,
                )
            )
            if existing is None:
                destinations = [step.destination_id for step in steps_by_policy.get(policy.id, []) if step.enabled]
        if destinations:
            due.append((alert, policy, destinations))
    return due


def due_for_repeat(session: Session, *, now=None) -> list[tuple[AlertRow, NotificationPolicyRow]]:
    current = now or utcnow()
    policies = {row.id: row for row in session.scalars(select(NotificationPolicyRow))}
    due: list[tuple[AlertRow, NotificationPolicyRow]] = []
    for alert in session.scalars(select(AlertRow).where(AlertRow.status.in_(ACTIVE_STATUSES))):
        if alert.status != AlertStatus.OPEN:
            continue
        policy = policies.get(alert.policy_id)
        if policy is None or not policy.repeat_after_seconds:
            continue
        last = session.scalar(
            select(NotificationDeliveryRow)
            .where(
                NotificationDeliveryRow.alert_id == alert.id,
                NotificationDeliveryRow.status == DeliveryStatus.SENT,
            )
            .order_by(NotificationDeliveryRow.sent_at.desc())
        )
        reference = last.sent_at if last is not None and last.sent_at else alert.first_seen_at
        if _aware(current) - _aware(reference) < timedelta(seconds=policy.repeat_after_seconds):
            continue
        due.append((alert, policy))
    return due
