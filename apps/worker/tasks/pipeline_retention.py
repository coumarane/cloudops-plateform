from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_PIPELINE_RETENTION
from app.services.pipeline_sync import run_pipeline_retention
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.pipeline_retention.prune_history", bind=True, acks_late=True, max_retries=3)
def prune_history(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting pipeline retention job_id=%s", job_id)
    try:
        return run_pipeline_retention(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=60) from error


@celery_app.task(name="tasks.pipeline_retention.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_PIPELINE_RETENTION)
    return 1
