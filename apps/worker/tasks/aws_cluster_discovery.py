from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.providers.aws.errors import AwsAuthError, AwsPermissionError, AwsTransientError
from app.services.aws_sync import run_cluster_discovery
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="tasks.aws_cluster_discovery.discover_clusters",
    bind=True,
    autoretry_for=(AwsTransientError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def discover_clusters(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting EKS cluster discovery job_id=%s", job_id)
    try:
        return run_cluster_discovery(job_id)
    except (AwsAuthError, AwsPermissionError):
        logger.exception("Non-retryable AWS error during cluster discovery")
        raise
