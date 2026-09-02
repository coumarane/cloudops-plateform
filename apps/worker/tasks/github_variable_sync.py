from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.github_sync import run_variable_sync
from app.services.job_kinds import KIND_GITHUB_VARIABLE_SYNC
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.github_variable_sync.sync_variables", bind=True, acks_late=True, max_retries=3)
def sync_variables(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting GitHub variable sync job_id=%s", job_id)
    return run_variable_sync(job_id)


@celery_app.task(name="tasks.github_variable_sync.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_GITHUB_VARIABLE_SYNC)
    return 1
