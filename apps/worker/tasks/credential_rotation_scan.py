from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.credential_jobs import run_rotation_status_scan
from app.services.job_kinds import KIND_CREDENTIAL_ROTATION_SCAN
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="tasks.credential_rotation_scan.scan_rotation_status",
    bind=True,
    acks_late=True,
)
def scan_rotation_status(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting credential rotation status scan job_id=%s", job_id)
    return run_rotation_status_scan(job_id)


@celery_app.task(name="tasks.credential_rotation_scan.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    job = enqueue_job(KIND_CREDENTIAL_ROTATION_SCAN)
    return 1 if job else 0
