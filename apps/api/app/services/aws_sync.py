from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

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
from app.topology.loader import load_topology
from app.topology.models import AccountBinding, environment_scope_id

logger = get_logger(__name__)


def _run_bounded(items: list, fn, max_workers: int) -> list[tuple[object, object, Exception | None]]:
    if not items:
        return []
    workers = max(1, min(max_workers, len(items)))
    results: list[tuple[object, object, Exception | None]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, item): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                results.append((item, future.result(), None))
            except Exception as error:  # noqa: BLE001 - isolate per-account failures
                results.append((item, None, error))
    return results


def discover_account(account: AccountBinding) -> int:
    factory = AwsClientFactory(config=account.connection_config())
    clusters = EksDiscovery(factory, account.connection_config()).list_clusters(account.environments)
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        grouped: dict[str, list[DiscoveredCluster]] = {environment: [] for environment in account.environments}
        for cluster in clusters:
            grouped.setdefault(cluster.environment, []).append(cluster)
        for environment in account.environments:
            env_id = environment_scope_id(account.alias, environment)
            repo.replace_clusters_for_scope(
                grouped.get(environment, []),
                platform_region=account.logical_region,
                environment=environment,
            )
            repo.mark_scope_success(env_id, "discovery")
        session.commit()
        logger.info("Account discovery stored alias=%s count=%s", account.alias, len(clusters))
        return len(clusters)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def health_account(account: AccountBinding) -> int:
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        rows = [
            row
            for row in repo.present_clusters()
            if row.account_alias == account.alias and row.cloud_region == account.cloud_region
        ]
        if not rows:
            for environment in account.environments:
                repo.mark_scope_success(environment_scope_id(account.alias, environment), "health")
            session.commit()
            return 0
        factory = AwsClientFactory(config=account.connection_config())
        discovery = EksDiscovery(factory, account.connection_config())
        collector = ClusterHealthCollector(factory)
        count = 0
        for row in rows:
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
        for environment in account.environments:
            repo.mark_scope_success(environment_scope_id(account.alias, environment), "health")
        session.commit()
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def certificates_account(account: AccountBinding) -> int:
    factory = AwsClientFactory(config=account.connection_config())
    certificates = AcmScanner(factory, account.connection_config()).list_certificates()
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        repo.replace_certificates_for_account(
            certificates,
            account_alias=account.alias,
            platform_region=account.logical_region,
        )
        session.commit()
        return len(certificates)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _record_account_errors(account: AccountBinding, error: Exception) -> None:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        for environment in account.environments:
            repo.mark_scope_error(environment_scope_id(account.alias, environment), error)
        session.commit()
    finally:
        session.close()


def _finish_fleet_job(job_id: str, *, kind: str, results: list[tuple[AccountBinding, object, Exception | None]]) -> int:
    succeeded = [(account, value) for account, value, error in results if error is None]
    failed = [(account, error) for account, _value, error in results if error is not None]
    total = sum(int(value or 0) for _account, value in succeeded)
    for account, error in failed:
        mapped = classify_aws_error(error)
        logger.warning("Account %s failed during %s error=%s", account.alias, kind, mapped)
        _record_account_errors(account, mapped)
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        if not succeeded and failed:
            first = classify_aws_error(failed[0][1])
            repo.mark_job_finished(
                job_id,
                status="failed",
                detail=sanitize_text(str(first)),
                error_class=first.__class__.__name__,
            )
            session.commit()
            if isinstance(first, AwsTransientError):
                raise first
            if isinstance(first, (AwsAuthError, AwsPermissionError)):
                raise first
            raise first
        failed_aliases = ", ".join(account.alias for account, _error in failed) or "none"
        detail = (
            f"{kind}: {len(succeeded)}/{len(results)} accounts succeeded "
            f"({total} records). Failed: {failed_aliases}"
        )
        repo.mark_job_finished(job_id, status="succeeded", detail=detail)
        session.commit()
        return total
    finally:
        session.close()


def run_cluster_discovery(job_id: str) -> int:
    topology = load_topology()
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_running(job_id)
        session.commit()
    finally:
        session.close()
    results = _run_bounded(list(topology.accounts), discover_account, topology.scan_concurrency)
    return _finish_fleet_job(job_id, kind="discovery", results=results)


def run_health_scan(job_id: str) -> int:
    topology = load_topology()
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_running(job_id)
        session.commit()
    finally:
        session.close()
    results = _run_bounded(list(topology.accounts), health_account, topology.scan_concurrency)
    return _finish_fleet_job(job_id, kind="health", results=results)


def run_certificate_scan(job_id: str) -> int:
    topology = load_topology()
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_running(job_id)
        session.commit()
    finally:
        session.close()
    results = _run_bounded(list(topology.accounts), certificates_account, topology.scan_concurrency)
    return _finish_fleet_job(job_id, kind="certificates", results=results)
