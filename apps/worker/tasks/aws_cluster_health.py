from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.providers.aws.errors import AwsAuthError, AwsPermissionError, AwsTransientError
from app.services.aws_sync import run_health_scan
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="tasks.aws_cluster_health.scan_health",
    bind=True,
    autoretry_for=(AwsTransientError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def scan_health(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting EKS health scan job_id=%s", job_id)
    try:
        return run_health_scan(job_id)
    except (AwsAuthError, AwsPermissionError):
        logger.exception("Non-retryable AWS error during health scan")
        raise
