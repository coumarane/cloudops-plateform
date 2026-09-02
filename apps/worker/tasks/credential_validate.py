from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.core.logging import sanitize_text
from app.services.credential_jobs import run_credential_validation
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="tasks.credential_validate.validate_credential",
    bind=True,
    acks_late=True,
)
def validate_credential(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting credential validation job_id=%s", job_id)
    try:
        return run_credential_validation(job_id)
    except Exception:
        logger.exception(sanitize_text("Credential validation failed"))
        raise
