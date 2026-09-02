from __future__ import annotations

from sqlalchemy.orm import Session

from app.alerting.service import run_alert_evaluate, run_escalation, run_suppression_expiry, run_maintenance_expiry
from app.notifications.dispatcher import dispatch_pending


def evaluate(session: Session) -> int:
    """Evaluate suppressions, due notifications, and escalations in bulk."""
    return run_alert_evaluate(session)


def dispatch_notifications(session: Session) -> int:
    return dispatch_pending(session)


def check_escalation(session: Session) -> int:
    return run_escalation(session)


def expire_suppressions_and_windows(session: Session) -> int:
    return run_suppression_expiry(session) + run_maintenance_expiry(session)
