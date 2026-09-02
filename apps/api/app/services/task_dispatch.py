from __future__ import annotations

from app.core.config import settings
from app.core.correlation import bind_correlation_id
from app.core.logging import get_logger
from app.services.aws_sync import run_certificate_scan, run_cluster_discovery, run_health_scan
from app.services.job_kinds import KIND_CERTIFICATES, KIND_DISCOVERY, KIND_HEALTH, TASK_NAMES

logger = get_logger(__name__)


def _run_inline(kind: str, job_id: str) -> None:
    if kind == KIND_DISCOVERY:
        run_cluster_discovery(job_id)
    elif kind == KIND_HEALTH:
        run_health_scan(job_id)
    elif kind == KIND_CERTIFICATES:
        run_certificate_scan(job_id)
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
