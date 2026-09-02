from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_HTTP_HEALTH_CHECK
from app.services.health_sync import run_http_health_check
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.http_health_check.check_endpoints", bind=True, acks_late=True, max_retries=3)
def check_endpoints(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting HTTP health checks job_id=%s", job_id)
    try:
        return run_http_health_check(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=30) from error


@celery_app.task(name="tasks.http_health_check.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_HTTP_HEALTH_CHECK)
    return 1
