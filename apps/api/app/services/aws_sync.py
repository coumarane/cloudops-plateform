from __future__ import annotations

from app.core.logging import get_logger, sanitize_text
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.providers.aws.acm import AcmScanner
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.eks import EksDiscovery
from app.providers.aws.errors import AwsAuthError, AwsPermissionError, AwsTransientError, classify_aws_error
from app.providers.aws.k8s import ClusterHealthCollector
from app.providers.aws.models import DiscoveredCluster
from app.services.mappers import discovered_from_row

logger = get_logger(__name__)


def _session_factory() -> AwsClientFactory:
    return AwsClientFactory()


def run_cluster_discovery(job_id: str) -> int:
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        repo.mark_job_running(job_id)
        session.commit()
        factory = _session_factory()
        clusters = EksDiscovery(factory).list_dev_clusters()
        repo.replace_clusters(clusters)
        repo.mark_job_finished(job_id, status="succeeded", detail=f"Discovered {len(clusters)} EKS clusters")
        session.commit()
        logger.info("Cluster discovery stored count=%s", len(clusters))
        return len(clusters)
    except Exception as error:
        session.rollback()
        mapped = classify_aws_error(error)
        _fail_job(job_id, mapped)
        if isinstance(mapped, AwsTransientError):
            raise
        if isinstance(mapped, (AwsAuthError, AwsPermissionError)):
            raise
        raise
    finally:
        session.close()


def run_health_scan(job_id: str) -> int:
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        repo.mark_job_running(job_id)
        session.commit()
        factory = _session_factory()
        discovery = EksDiscovery(factory)
        collector = ClusterHealthCollector(factory)
        count = 0
        for row in repo.present_clusters():
            cluster: DiscoveredCluster = discovered_from_row(row)
            try:
                raw = discovery.describe_raw(row.name)
                cluster.endpoint = raw.get("endpoint")
                ca_data = (raw.get("certificateAuthority") or {}).get("data")
                snapshot = collector.collect(cluster, ca_data)
            except Exception as error:
                mapped = classify_aws_error(error)
                if isinstance(mapped, AwsTransientError):
                    raise
                logger.warning("Health scan skipped cluster=%s error=%s", row.name, mapped)
                continue
            repo.upsert_health(row.id, snapshot)
            count += 1
        repo.mark_job_finished(job_id, status="succeeded", detail=f"Scanned health for {count} clusters")
        session.commit()
        return count
    except Exception as error:
        session.rollback()
        mapped = classify_aws_error(error)
        _fail_job(job_id, mapped)
        raise
    finally:
        session.close()


def run_certificate_scan(job_id: str) -> int:
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        repo.mark_job_running(job_id)
        session.commit()
        certificates = AcmScanner(_session_factory()).list_certificates()
        repo.replace_certificates(certificates)
        repo.mark_job_finished(job_id, status="succeeded", detail=f"Scanned {len(certificates)} ACM certificates")
        session.commit()
        return len(certificates)
    except Exception as error:
        session.rollback()
        mapped = classify_aws_error(error)
        _fail_job(job_id, mapped)
        raise
    finally:
        session.close()


def _fail_job(job_id: str, error: Exception) -> None:
    detail = sanitize_text(str(error))
    error_class = error.__class__.__name__
    retry_session = SessionLocal()
    try:
        InventoryRepository(retry_session).mark_job_finished(
            job_id,
            status="failed",
            detail=detail,
            error_class=error_class,
        )
        retry_session.commit()
    finally:
        retry_session.close()
