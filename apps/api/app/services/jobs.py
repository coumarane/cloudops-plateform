from __future__ import annotations

from app.core.correlation import current_correlation_id
from app.core.logging import get_logger
from app.db.models import PlatformJobRow
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.services.job_kinds import JOB_NAMES, JOB_PROVIDERS
from app.services.task_dispatch import submit_job

logger = get_logger(__name__)


def enqueue_job(
    kind: str,
    *,
    target_id: str = "",
    provider: str | None = None,
    platform_region: str | None = None,
    environment: str | None = None,
) -> PlatformJobRow:
    correlation_id = current_correlation_id()
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        existing = repo.find_running_job(kind, target_id=target_id)
        if existing:
            session.commit()
            return existing
        job = repo.create_job(
            kind,
            JOB_NAMES[kind],
            correlation_id,
            provider=provider or JOB_PROVIDERS.get(kind, "AWS"),
            target_id=target_id,
            platform_region=platform_region,
            environment=environment,
        )
        session.commit()
        session.refresh(job)
        try:
            submit_job(kind, job.id, job.correlation_id)
        except Exception as error:
            logger.warning("Job kind=%s id=%s finished with error=%s", kind, job.id, error)
        session.refresh(job)
        logger.info("Enqueued job kind=%s id=%s status=%s", kind, job.id, job.status)
        return job
    finally:
        session.close()
