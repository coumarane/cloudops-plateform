from celery.utils.log import get_task_logger

from app.core.correlation import bind_correlation_id
from app.db.models import PlatformJobRow
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.services.github_webhooks import process_delivery
from celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.github_webhook.process_delivery", bind=True, acks_late=True, max_retries=3)
def process_delivery_task(self, job_id: str, correlation_id: str) -> int:
    bind_correlation_id(correlation_id)
    session = SessionLocal()
    try:
        job = session.get(PlatformJobRow, job_id)
        target = job.target_id if job else job_id
    finally:
        session.close()
    logger.info("Processing GitHub webhook delivery target=%s", target)
    process_delivery(target)
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_finished(job_id, status="succeeded", detail="github-webhook-process")
        session.commit()
    finally:
        session.close()
    return 1
