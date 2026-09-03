from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_ALERT_NOTIFICATION_DISPATCH
from app.alerting.jobs import run_dispatch_job
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.alert_notification_dispatch.dispatch", bind=True, acks_late=True, max_retries=3)
def dispatch(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting alert notification dispatch job_id=%s", job_id)
    try:
        return run_dispatch_job(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=30) from error


@celery_app.task(name="tasks.alert_notification_dispatch.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_ALERT_NOTIFICATION_DISPATCH)
    return 1
