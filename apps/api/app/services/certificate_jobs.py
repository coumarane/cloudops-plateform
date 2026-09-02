from __future__ import annotations

from datetime import datetime, timezone

from app.core.logging import get_logger, sanitize_text
from app.core.metrics import inc, observe_duration
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.services.certificate_monitor import evaluate_alerts, refresh_days

logger = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_certificate_discovery(job_id: str) -> int:
    from app.services.alibaba_sync import scan_alibaba_certificates
    from app.services.aws_sync import scan_aws_certificates

    started = utcnow()
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        repo.mark_job_running(job_id)
        session.commit()
    finally:
        session.close()

    total = 0
    parts: list[str] = []
    try:
        aws_count = scan_aws_certificates()
        total += aws_count
        parts.append(f"aws={aws_count}")
    except Exception as error:
        logger.warning("AWS certificate discovery failed error=%s", error)
        inc("cloudops_certificate_scan_failures_total", {"provider": "aws", "job": "discovery"})
        parts.append("aws=failed")
    try:
        alibaba_count = scan_alibaba_certificates()
        total += alibaba_count
        parts.append(f"alibaba={alibaba_count}")
    except Exception as error:
        logger.warning("Alibaba certificate discovery failed error=%s", error)
        inc("cloudops_certificate_scan_failures_total", {"provider": "alibaba", "job": "discovery"})
        parts.append("alibaba=failed")

    monitor = SessionLocal()
    try:
        refresh_days(monitor)
        evaluate_alerts(monitor)
        monitor.commit()
    except Exception:
        monitor.rollback()
        raise
    finally:
        monitor.close()

    finish = SessionLocal()
    try:
        status = "failed" if parts and all("failed" in part for part in parts) and total == 0 else "succeeded"
        InventoryRepository(finish).mark_job_finished(
            job_id,
            status=status,
            detail=sanitize_text(f"certificate-discovery: {', '.join(parts)} ({total} records)"),
            error_class="" if status == "succeeded" else "PartialFailure",
        )
        finish.commit()
    finally:
        finish.close()
    observe_duration(
        "cloudops_certificate_scan_duration_seconds",
        {"job": "discovery"},
        (utcnow() - started).total_seconds(),
    )
    return total
