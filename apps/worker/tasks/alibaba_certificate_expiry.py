from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.providers.alibaba.exceptions import AlibabaAuthError, AlibabaPermissionError, AlibabaTransientError
from app.services.alibaba_sync import run_certificate_expiry_scan
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="tasks.alibaba_certificate_expiry.scan_expiry",
    bind=True,
    autoretry_for=(AlibabaTransientError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def scan_expiry(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting Alibaba certificate expiry scan job_id=%s", job_id)
    try:
        return run_certificate_expiry_scan(job_id)
    except (AlibabaAuthError, AlibabaPermissionError):
        logger.exception("Non-retryable Alibaba error during certificate expiry scan")
        raise
