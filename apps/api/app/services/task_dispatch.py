from __future__ import annotations

from app.core.config import settings
from app.core.correlation import bind_correlation_id
from app.core.logging import get_logger
from app.services.alibaba_sync import (
    run_account_validation as run_alibaba_validation,
    run_certificate_expiry_scan as run_alibaba_cert_expiry,
    run_certificate_scan as run_alibaba_certificates,
    run_cluster_discovery as run_alibaba_discovery,
    run_health_scan as run_alibaba_health,
)
from app.services.aws_sync import run_certificate_scan, run_cluster_discovery, run_health_scan
from app.services.certificate_jobs import run_certificate_discovery
from app.services.certificate_monitor import (
    run_alert_evaluation,
    run_certificate_validate,
    run_endpoint_validation,
    run_expiry_scan,
)
from app.services.credential_jobs import run_credential_validation, run_rotation_status_scan
from app.services.job_kinds import (
    KIND_ALIBABA_CERT_EXPIRY,
    KIND_ALIBABA_CERTIFICATES,
    KIND_ALIBABA_DISCOVERY,
    KIND_ALIBABA_HEALTH,
    KIND_ALIBABA_VALIDATION,
    KIND_CERTIFICATE_ALERTS,
    KIND_CERTIFICATE_DISCOVERY,
    KIND_CERTIFICATE_ENDPOINT,
    KIND_CERTIFICATE_EXPIRY,
    KIND_CERTIFICATE_VALIDATE,
    KIND_CERTIFICATES,
    KIND_CREDENTIAL_ROTATION_SCAN,
    KIND_CREDENTIAL_VALIDATE,
    KIND_DISCOVERY,
    KIND_GITHUB_REPOSITORY_SYNC,
    KIND_GITHUB_SECRET_SYNC,
    KIND_GITHUB_VARIABLE_SYNC,
    KIND_GITHUB_WEBHOOK,
    KIND_GITHUB_WORKFLOW_RUN_SYNC,
    KIND_GITHUB_WORKFLOW_SYNC,
    KIND_HEALTH,
    TASK_NAMES,
)

logger = get_logger(__name__)


def _run_inline(kind: str, job_id: str) -> None:
    if kind == KIND_DISCOVERY:
        run_cluster_discovery(job_id)
    elif kind == KIND_HEALTH:
        run_health_scan(job_id)
    elif kind == KIND_CERTIFICATES:
        run_certificate_scan(job_id)
    elif kind == KIND_ALIBABA_VALIDATION:
        run_alibaba_validation(job_id)
    elif kind == KIND_ALIBABA_DISCOVERY:
        run_alibaba_discovery(job_id)
    elif kind == KIND_ALIBABA_HEALTH:
        run_alibaba_health(job_id)
    elif kind == KIND_ALIBABA_CERTIFICATES:
        run_alibaba_certificates(job_id)
    elif kind == KIND_ALIBABA_CERT_EXPIRY:
        run_alibaba_cert_expiry(job_id)
    elif kind == KIND_CREDENTIAL_VALIDATE:
        run_credential_validation(job_id)
    elif kind == KIND_CREDENTIAL_ROTATION_SCAN:
        run_rotation_status_scan(job_id)
    elif kind == KIND_CERTIFICATE_DISCOVERY:
        run_certificate_discovery(job_id)
    elif kind == KIND_CERTIFICATE_EXPIRY:
        run_expiry_scan(job_id)
    elif kind == KIND_CERTIFICATE_ENDPOINT:
        run_endpoint_validation(job_id)
    elif kind == KIND_CERTIFICATE_ALERTS:
        run_alert_evaluation(job_id)
    elif kind == KIND_CERTIFICATE_VALIDATE:
        run_certificate_validate(job_id)
    elif kind == KIND_GITHUB_REPOSITORY_SYNC:
        from app.services.github_sync import run_repository_sync

        run_repository_sync(job_id)
    elif kind == KIND_GITHUB_WORKFLOW_SYNC:
        from app.services.github_sync import run_workflow_sync

        run_workflow_sync(job_id)
    elif kind == KIND_GITHUB_WORKFLOW_RUN_SYNC:
        from app.services.github_sync import run_workflow_run_sync

        run_workflow_run_sync(job_id)
    elif kind == KIND_GITHUB_VARIABLE_SYNC:
        from app.services.github_sync import run_variable_sync

        run_variable_sync(job_id)
    elif kind == KIND_GITHUB_SECRET_SYNC:
        from app.services.github_sync import run_secret_metadata_sync

        run_secret_metadata_sync(job_id)
    elif kind == KIND_GITHUB_WEBHOOK:
        from app.services.github_webhooks import process_delivery
        from app.db.session import SessionLocal
        from app.db.models import PlatformJobRow

        session = SessionLocal()
        try:
            job = session.get(PlatformJobRow, job_id)
            target = job.target_id if job else job_id
        finally:
            session.close()
        process_delivery(target)
        session = SessionLocal()
        try:
            from app.db.repository import InventoryRepository

            InventoryRepository(session).mark_job_finished(job_id, status="succeeded", detail="github-webhook-process")
            session.commit()
        finally:
            session.close()
    else:
        raise ValueError(kind)


def submit_job(kind: str, job_id: str, correlation_id: str) -> None:
    bind_correlation_id(correlation_id)
    if settings.celery_eager:
        logger.info("Running job inline kind=%s id=%s", kind, job_id)
        _run_inline(kind, job_id)
        return
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[3] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from celery_app import celery_app

    celery_app.send_task(TASK_NAMES[kind], args=[job_id, correlation_id])
