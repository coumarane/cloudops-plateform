from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.config import settings
from app.core.logging import get_logger, sanitize_text
from app.db.models import PlatformJobRow
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.providers.aws.acm import AcmScanner
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.eks import EksDiscovery
from app.providers.aws.errors import AwsTransientError, classify_aws_error
from app.providers.alibaba.exceptions import AlibabaIntegrationError, classify_alibaba_error
from app.providers.aws.k8s import ClusterHealthCollector
from app.providers.aws.models import DiscoveredCertificate, DiscoveredCluster
from app.providers.kubernetes.collector import inventory_payload
from app.services.mappers import discovered_from_row
from app.platform.fleet import accounts_for_job
from app.providers.factory import provider_adapter
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
    return provider_adapter("AWS").discover_clusters(account)


def health_account(account: AccountBinding, clusters: list[tuple[str, DiscoveredCluster]]) -> list[tuple]:
    return provider_adapter("AWS").collect_health(account, clusters)


def certificates_account(account: AccountBinding) -> list[DiscoveredCertificate]:
    discovered = list(provider_adapter("AWS").discover_certificates(account))
    if settings.provider_stub:
        return discovered
    try:
        factory = AwsClientFactory(config=account.connection_config())
        discovered.extend(_eks_tls_certificates(account, factory))
    except Exception as error:
        logger.warning("EKS TLS certificate scan skipped account=%s error=%s", account.alias, classify_aws_error(error))
    return discovered


def _eks_tls_certificates(account: AccountBinding, factory: AwsClientFactory) -> list[DiscoveredCertificate]:
    from app.providers.aws.eks import EksDiscovery
    from app.providers.aws.k8s import eks_bearer_token
    from app.providers.common.k8s_certs import apply_ingress_usage, discovered_from_tls_secret, ingress_secret_hosts

    session = SessionLocal()
    try:
        rows = [
            row
            for row in InventoryRepository(session).present_clusters()
            if row.account_alias == account.alias and row.provider == "AWS"
        ]
        clusters = [discovered_from_row(row) for row in rows]
        cluster_ids = {row.name: row.id for row in rows}
    finally:
        session.close()
    if not clusters:
        return []
    discovery = EksDiscovery(factory, account.connection_config())
    found: list[DiscoveredCertificate] = []
    for cluster in clusters:
        try:
            raw = discovery.describe_raw(cluster.name)
            cluster.endpoint = raw.get("endpoint") or cluster.endpoint
            token = eks_bearer_token(factory, cluster.name, cluster.cloud_region)
            from kubernetes import client

            configuration = client.Configuration()
            configuration.host = cluster.endpoint
            configuration.verify_ssl = False
            configuration.api_key = {"authorization": f"Bearer {token}"}
            api_client = client.ApiClient(configuration)
            core = client.CoreV1Api(api_client)
            secrets = core.list_secret_for_all_namespaces().items
            ingress_hosts: dict[tuple[str, str], list[str]] = {}
            try:
                networking = client.NetworkingV1Api(api_client)
                ingress_hosts = ingress_secret_hosts(networking.list_ingress_for_all_namespaces().items)
            except Exception:
                ingress_hosts = {}
            cluster_certs: list[DiscoveredCertificate] = []
            for secret in secrets:
                if getattr(secret, "type", "") != "kubernetes.io/tls":
                    continue
                payload = {
                    "metadata": {
                        "name": secret.metadata.name,
                        "namespace": secret.metadata.namespace,
                    },
                    "data": dict(secret.data or {}),
                }
                payload["data"].pop("tls.key", None)
                namespace = str(secret.metadata.namespace or "default")
                name = str(secret.metadata.name)
                arn = (
                    f"arn:aws:eks:{cluster.cloud_region}:{cluster.aws_account_id}:secret/"
                    f"{cluster.name}/{namespace}/{name}"
                )
                parsed = discovered_from_tls_secret(
                    payload,
                    arn=arn,
                    provider="AWS",
                    platform_region=cluster.platform_region,
                    account_alias=cluster.account_alias,
                    cloud_region=cluster.cloud_region,
                    cluster_name=cluster.name,
                    cluster_id=cluster_ids.get(cluster.name, ""),
                    environment=cluster.environment,
                )
                if parsed is not None:
                    cluster_certs.append(parsed)
            apply_ingress_usage(cluster_certs, ingress_hosts)
            found.extend(cluster_certs)
        except Exception as error:
            logger.warning("EKS TLS listing skipped cluster=%s error=%s", cluster.name, classify_aws_error(error))
    return found


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


def _store_health(account: AccountBinding, snapshots: list[tuple], repo: InventoryRepository) -> int:
    from app.services.health_sync import persist_account_health

    return persist_account_health(account, snapshots, repo)


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
            for environment in account.environments:
                repo.mark_scope_attempted(environment_scope_id(account.alias, environment))
            if error is not None:
                failed.append((account, classify_job_error(error)))
                from app.core.metrics import inc as metrics_inc

                metrics_inc(
                    "cloudops_certificate_scan_failures_total",
                    {
                        "provider": account.provider.lower(),
                        "region": account.logical_region.lower(),
                        "environment": (account.environments[0] if account.environments else "dev").lower(),
                    },
                )
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
            status = "partial" if failed and succeeded else "succeeded"
            if not results:
                status = "succeeded"
                detail = f"{kind}: no accounts in scope"
            job = session.get(PlatformJobRow, job_id)
            if job is not None:
                job.resources_found = total
                job.error_count = len(failed)
            repo.mark_job_finished(job_id, status=status, detail=detail)
            session.commit()
            return total
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    raise first


def run_cluster_discovery(job_id: str) -> int:
    accounts = accounts_for_job(job_id, "AWS")
    _mark_job_running(job_id)
    results = _run_bounded(accounts, discover_account, max(1, len(accounts) or 1))
    return _finish_fleet_job(job_id, kind="discovery", results=results, persist=_store_discovery)


def run_health_scan(job_id: str) -> int:
    accounts = accounts_for_job(job_id, "AWS")
    _mark_job_running(job_id)
    clusters = _clusters_by_account(accounts)

    def collect(account: AccountBinding):
        return health_account(account, clusters.get(account.alias, []))

    results = _run_bounded(accounts, collect, max(1, len(accounts) or 1))
    return _finish_fleet_job(job_id, kind="health", results=results, persist=_store_health)


def persist_certificate_results(results: list[tuple[AccountBinding, object, Exception | None]]) -> int:
    session = SessionLocal()
    repo = InventoryRepository(session)
    try:
        total = 0
        for account, value, error in results:
            for environment in account.environments:
                repo.mark_scope_attempted(environment_scope_id(account.alias, environment))
            if error is not None:
                mapped = classify_job_error(error)
                logger.warning("Account %s failed during certificates error=%s", account.alias, mapped)
                from app.core.metrics import inc as metrics_inc

                metrics_inc(
                    "cloudops_certificate_scan_failures_total",
                    {
                        "provider": account.provider.lower(),
                        "region": account.logical_region.lower(),
                    },
                )
                for environment in account.environments:
                    repo.mark_scope_error(environment_scope_id(account.alias, environment), mapped)
                continue
            total += int(_store_certificates(account, value, repo) or 0)
        session.commit()
        return total
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def scan_aws_certificates() -> int:
    accounts = accounts_for_job("", "AWS")
    results = _run_bounded(accounts, certificates_account, max(1, len(accounts) or 1))
    return persist_certificate_results(results)


def run_certificate_scan(job_id: str) -> int:
    accounts = accounts_for_job(job_id, "AWS")
    _mark_job_running(job_id)
    results = _run_bounded(accounts, certificates_account, max(1, len(accounts) or 1))
    return _finish_fleet_job(job_id, kind="certificates", results=results, persist=_store_certificates)
