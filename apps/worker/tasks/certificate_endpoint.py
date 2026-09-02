from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.certificate_monitor import run_endpoint_validation
from app.services.job_kinds import KIND_CERTIFICATE_ENDPOINT
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.certificate_endpoint.validate_endpoints", bind=True, acks_late=True, max_retries=3)
def validate_endpoints(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting certificate endpoint validation job_id=%s", job_id)
    return run_endpoint_validation(job_id)


@celery_app.task(name="tasks.certificate_endpoint.periodic_scan")
def periodic_scan() -> int:
    from app.services.jobs import enqueue_job

    job = enqueue_job(KIND_CERTIFICATE_ENDPOINT)
    return 1 if job else 0
