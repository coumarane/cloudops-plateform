from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_HEALTH_ALERT_EVALUATION
from app.services.health_sync import run_health_alert_evaluation
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.health_alert_evaluation.evaluate", bind=True, acks_late=True, max_retries=3)
def evaluate(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting health alert evaluation job_id=%s", job_id)
    try:
        return run_health_alert_evaluation(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=30) from error


@celery_app.task(name="tasks.health_alert_evaluation.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_HEALTH_ALERT_EVALUATION)
    return 1
