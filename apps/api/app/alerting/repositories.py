from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting.models import ACTIVE_STATUSES, AlertStatus
from app.db.models import (
    AlertEventRow,
    AlertRow,
    AlertRuleRow,
    AlertRoutingRuleRow,
    NotificationDestinationRow,
    NotificationPolicyRow,
    NotificationPolicyStepRow,
)


def active_by_fingerprint(session: Session, fingerprint: str) -> AlertRow | None:
    return session.scalar(
        select(AlertRow)
        .where(AlertRow.fingerprint == fingerprint, AlertRow.status.in_(ACTIVE_STATUSES))
        .order_by(AlertRow.last_seen_at.desc())
    )


def latest_by_fingerprint(session: Session, fingerprint: str) -> AlertRow | None:
    return session.scalar(select(AlertRow).where(AlertRow.fingerprint == fingerprint).order_by(AlertRow.last_seen_at.desc()))


def list_alerts(session: Session) -> list[AlertRow]:
    return list(session.scalars(select(AlertRow).order_by(AlertRow.last_seen_at.desc())))


def list_events(session: Session, alert_id: str) -> list[AlertEventRow]:
    return list(
        session.scalars(select(AlertEventRow).where(AlertEventRow.alert_id == alert_id).order_by(AlertEventRow.created_at.asc()))
    )


def list_rules(session: Session) -> list[AlertRuleRow]:
    return list(session.scalars(select(AlertRuleRow)))


def list_routes(session: Session) -> list[AlertRoutingRuleRow]:
    return list(session.scalars(select(AlertRoutingRuleRow)))


def list_destinations(session: Session) -> list[NotificationDestinationRow]:
    return list(session.scalars(select(NotificationDestinationRow)))


def list_policies(session: Session) -> list[NotificationPolicyRow]:
    return list(session.scalars(select(NotificationPolicyRow)))


def policy_steps(session: Session, policy_id: str, step_type: str | None = None) -> list[NotificationPolicyStepRow]:
    query = select(NotificationPolicyStepRow).where(NotificationPolicyStepRow.policy_id == policy_id)
    if step_type:
        query = query.where(NotificationPolicyStepRow.step_type == step_type)
    return list(session.scalars(query))


def open_alerts(session: Session) -> list[AlertRow]:
    return list(session.scalars(select(AlertRow).where(AlertRow.status.in_((AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)))))
