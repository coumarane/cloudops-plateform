from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.services.pipeline_webhooks import process_pipeline_delivery
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.pipeline_webhook.process_delivery", bind=True, acks_late=True, max_retries=3)
def process_delivery(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    logger.info("Starting pipeline webhook processing job_id=%s", job_id)
    from app.db.models import PlatformJobRow
    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        job = session.get(PlatformJobRow, job_id)
        target = job.target_id if job else job_id
    finally:
        session.close()
    try:
        process_pipeline_delivery(target)
    except Exception as error:
        raise self.retry(exc=error, countdown=10) from error
    return 1
