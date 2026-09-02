from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_HEALTH_AGGREGATION
from app.services.health_sync import run_health_aggregation
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.health_aggregation.aggregate", bind=True, acks_late=True, max_retries=3)
def aggregate(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting health aggregation job_id=%s", job_id)
    try:
        return run_health_aggregation(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=30) from error


@celery_app.task(name="tasks.health_aggregation.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_HEALTH_AGGREGATION)
    return 1
