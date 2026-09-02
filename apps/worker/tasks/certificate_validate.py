from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.certificate_monitor import run_certificate_validate
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.certificate_validate.validate_certificate", bind=True, acks_late=True, max_retries=3)
def validate_certificate(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting certificate validation job_id=%s", job_id)
    return run_certificate_validate(job_id)
