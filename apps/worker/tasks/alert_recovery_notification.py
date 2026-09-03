from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_ALERT_RECOVERY_NOTIFICATION
from app.alerting.jobs import run_recovery_job
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.alert_recovery_notification.notify", bind=True, acks_late=True, max_retries=3)
def notify(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting alert recovery notification job_id=%s", job_id)
    try:
        return run_recovery_job(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=30) from error


@celery_app.task(name="tasks.alert_recovery_notification.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_ALERT_RECOVERY_NOTIFICATION)
    return 1
