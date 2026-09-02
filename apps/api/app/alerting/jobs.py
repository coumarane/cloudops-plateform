from __future__ import annotations

from app.alerting.service import (
    ensure_defaults,
    run_alert_evaluate,
    run_escalation,
    run_maintenance_expiry,
    run_recovery_notification,
    run_suppression_expiry,
)
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.notifications.dispatcher import dispatch_pending


def _run(job_id: str, detail: str, callback) -> int:
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_running(job_id)
        session.commit()
        ensure_defaults(session)
        result = callback(session)
        session.commit()
        InventoryRepository(session).mark_job_finished(job_id, status="succeeded", detail=f"{detail}:{result}")
        session.commit()
        return int(result or 0)
    except Exception:
        session.rollback()
        InventoryRepository(session).mark_job_finished(job_id, status="failed", detail=detail)
        session.commit()
        raise
    finally:
        session.close()


def run_evaluate_job(job_id: str) -> int:
    return _run(job_id, "alert-evaluate", run_alert_evaluate)


def run_dispatch_job(job_id: str) -> int:
    return _run(job_id, "alert-notification-dispatch", dispatch_pending)


def run_escalation_job(job_id: str) -> int:
    return _run(job_id, "alert-escalation-check", run_escalation)


def run_recovery_job(job_id: str) -> int:
    return _run(job_id, "alert-recovery-notification", run_recovery_notification)


def run_suppression_expiry_job(job_id: str) -> int:
    return _run(job_id, "alert-suppression-expiry", run_suppression_expiry)


def run_maintenance_expiry_job(job_id: str) -> int:
    return _run(job_id, "maintenance-window-expiry", run_maintenance_expiry)
