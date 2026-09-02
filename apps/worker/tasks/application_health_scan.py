from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_APPLICATION_HEALTH_SCAN
from app.services.health_sync import run_application_health_scan
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.application_health_scan.scan_applications", bind=True, acks_late=True, max_retries=3)
def scan_applications(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting application health scan job_id=%s", job_id)
    try:
        return run_application_health_scan(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=30) from error


@celery_app.task(name="tasks.application_health_scan.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_APPLICATION_HEALTH_SCAN)
    return 1
