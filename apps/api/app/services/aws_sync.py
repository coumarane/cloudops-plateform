from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.logging import get_logger, sanitize_text
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.providers.aws.acm import AcmScanner
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.eks import EksDiscovery
from app.providers.aws.errors import AwsTransientError, classify_aws_error
from app.providers.alibaba.exceptions import AlibabaIntegrationError, classify_alibaba_error
from app.providers.aws.k8s import ClusterHealthCollector
from app.providers.aws.models import ClusterHealthSnapshot, DiscoveredCertificate, DiscoveredCluster
from app.services.mappers import discovered_from_row
from app.topology.loader import load_topology
from app.topology.models import AccountBinding, environment_scope_id

logger = get_logger(__name__)


def classify_job_error(error: Exception):
    if isinstance(error, AlibabaIntegrationError):
        return classify_alibaba_error(error)
    return classify_aws_error(error)


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


def discover_account(account: AccountBinding) -> list[DiscoveredCluster]:
    factory = AwsClientFactory(config=account.connection_config())
    return EksDiscovery(factory, account.connection_config()).list_clusters(account.environments)


def health_account(account: AccountBinding, clusters: list[tuple[str, DiscoveredCluster]]) -> list[tuple[str, ClusterHealthSnapshot]]:
    if not clusters:
        return []
    factory = AwsClientFactory(config=account.connection_config())
    discovery = EksDiscovery(factory, account.connection_config())
    collector = ClusterHealthCollector(factory)
    snapshots: list[tuple[str, ClusterHealthSnapshot]] = []
    for cluster_id, cluster in clusters:
        try:
            raw = discovery.describe_raw(cluster.name)
            cluster.endpoint = raw.get("endpoint")
            ca_data = (raw.get("certificateAuthority") or {}).get("data")
            snapshots.append((cluster_id, collector.collect(cluster, ca_data)))
        except Exception as error:
            mapped = classify_aws_error(error)
            if isinstance(mapped, AwsTransientError):
                raise
            logger.warning("Health scan skipped cluster=%s error=%s", cluster.name, mapped)
    return snapshots


def certificates_account(account: AccountBinding) -> list[DiscoveredCertificate]:
    factory = AwsClientFactory(config=account.connection_config())
    return AcmScanner(factory, account.connection_config()).list_certificates()


def _store_discovery(account: AccountBinding, clusters: list[DiscoveredCluster], repo: InventoryRepository) -> int:
    grouped: dict[str, list[DiscoveredCluster]] = {environment: [] for environment in account.environments}
    for cluster in clusters:
        grouped.setdefault(cluster.environment, []).append(cluster)
    for environment in account.environments:
        repo.replace_clusters_for_scope(
            grouped.get(environment, []),
            platform_region=account.logical_region,
            environment=environment,
            provider=account.provider,
        )
        repo.mark_scope_success(environment_scope_id(account.alias, environment), "discovery")
    logger.info("Account discovery stored alias=%s count=%s", account.alias, len(clusters))
    return len(clusters)


def _store_health(
    account: AccountBinding, snapshots: list[tuple[str, ClusterHealthSnapshot]], repo: InventoryRepository
) -> int:
    for cluster_id, snapshot in snapshots:
        repo.upsert_health(cluster_id, snapshot)
    for environment in account.environments:
        repo.mark_scope_success(environment_scope_id(account.alias, environment), "health")
    return len(snapshots)


def _store_certificates(
    account: AccountBinding, certificates: list[DiscoveredCertificate], repo: InventoryRepository
) -> int:
    repo.replace_certificates_for_account(
        certificates,
        account_alias=account.alias,
        platform_region=account.logical_region,
    )
    return len(certificates)


def _mark_job_running(job_id: str) -> None:
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_running(job_id)
        session.commit()
    finally:
        session.close()


def _clusters_by_account(accounts: list[AccountBinding]) -> dict[str, list[tuple[str, DiscoveredCluster]]]:
    cloud_by_alias = {account.alias: account.cloud_region for account in accounts}
    grouped: dict[str, list[tuple[str, DiscoveredCluster]]] = {account.alias: [] for account in accounts}
    session = SessionLocal()
    try:
        for row in InventoryRepository(session).present_clusters():
            if row.account_alias in grouped and row.cloud_region == cloud_by_alias[row.account_alias]:
                grouped[row.account_alias].append((row.id, discovered_from_row(row)))
        return grouped
    finally:
        session.close()


def _finish_fleet_job(
    job_id: str,
    *,
    kind: str,
    results: list[tuple[AccountBinding, object, Exception | None]],
    persist,
) -> int:
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        succeeded: list[AccountBinding] = []
        failed: list[tuple[AccountBinding, Exception]] = []
        total = 0
        for account, value, error in results:
            if error is not None:
                failed.append((account, classify_job_error(error)))
                continue
            total += int(persist(account, value, repo) or 0)
            succeeded.append(account)
        for account, mapped in failed:
            logger.warning("Account %s failed during %s error=%s", account.alias, kind, mapped)
            for environment in account.environments:
                repo.mark_scope_error(environment_scope_id(account.alias, environment), mapped)
        if not succeeded and failed:
            first = failed[0][1]
            repo.mark_job_finished(
                job_id,
                status="failed",
                detail=sanitize_text(str(first)),
                error_class=first.__class__.__name__,
            )
            session.commit()
        else:
            failed_aliases = ", ".join(account.alias for account, _error in failed) or "none"
            detail = (
                f"{kind}: {len(succeeded)}/{len(results)} accounts succeeded "
                f"({total} records). Failed: {failed_aliases}"
            )
            repo.mark_job_finished(job_id, status="succeeded", detail=detail)
            session.commit()
            return total
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    raise first


def run_cluster_discovery(job_id: str) -> int:
    topology = load_topology()
    _mark_job_running(job_id)
    results = _run_bounded(list(topology.accounts), discover_account, topology.scan_concurrency)
    return _finish_fleet_job(job_id, kind="discovery", results=results, persist=_store_discovery)


def run_health_scan(job_id: str) -> int:
    topology = load_topology()
    _mark_job_running(job_id)
    clusters = _clusters_by_account(list(topology.accounts))

    def collect(account: AccountBinding):
        return health_account(account, clusters.get(account.alias, []))

    results = _run_bounded(list(topology.accounts), collect, topology.scan_concurrency)
    return _finish_fleet_job(job_id, kind="health", results=results, persist=_store_health)


def run_certificate_scan(job_id: str) -> int:
    topology = load_topology()
    _mark_job_running(job_id)
    results = _run_bounded(list(topology.accounts), certificates_account, topology.scan_concurrency)
    return _finish_fleet_job(job_id, kind="certificates", results=results, persist=_store_certificates)
