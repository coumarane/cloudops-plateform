from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.job_kinds import KIND_CLUSTER_HEALTH_SCAN
from app.services.health_sync import run_cluster_health_scan
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.cluster_health_scan.scan_clusters", bind=True, acks_late=True, max_retries=3)
def scan_clusters(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting cluster health scan job_id=%s", job_id)
    try:
        return run_cluster_health_scan(job_id)
    except Exception as error:
        raise self.retry(exc=error, countdown=30) from error


@celery_app.task(name="tasks.cluster_health_scan.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    enqueue_job(KIND_CLUSTER_HEALTH_SCAN)
    return 1
