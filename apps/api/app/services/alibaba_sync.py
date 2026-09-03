from __future__ import annotations

from app.core.logging import get_logger
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.providers.alibaba.adapter import AlibabaProviderAdapter
from app.providers.alibaba.certificates import normalize_tls_secret
from app.providers.alibaba.client import AlibabaClientFactory
from app.providers.alibaba.exceptions import AlibabaTransientError, classify_alibaba_error
from app.providers.alibaba.k8s import kubeconfig_auth_material
from app.providers.common.k8s_certs import apply_ingress_usage, ingress_secret_hosts
from app.providers.common.models import DiscoveredCertificate, DiscoveredCluster
from app.services.aws_sync import _clusters_by_account, _finish_fleet_job, _mark_job_running, _run_bounded
from app.services.mappers import discovered_from_row
from app.platform.fleet import accounts_for_job
from app.providers.factory import provider_adapter
from app.topology.models import AccountBinding, environment_scope_id

logger = get_logger(__name__)
ADAPTER = AlibabaProviderAdapter()


def discover_account(account: AccountBinding) -> list[DiscoveredCluster]:
    return provider_adapter("Alibaba").discover_clusters(account)


def health_account(account: AccountBinding, clusters: list[tuple[str, DiscoveredCluster]]) -> list[tuple]:
    return provider_adapter("Alibaba").collect_health(account, clusters)


def certificates_account(account: AccountBinding) -> list[DiscoveredCertificate]:
    config = account.connection_config()
    factory = AlibabaClientFactory(config)
    try:
        certificates = provider_adapter("Alibaba").discover_certificates(account)
    except AlibabaTransientError:
        raise
    except Exception as error:
        logger.warning("CAS listing skipped account=%s error=%s", account.alias, classify_alibaba_error(error))
        certificates = []
    session = SessionLocal()
    try:
        rows = [
            row
            for row in InventoryRepository(session).present_clusters()
            if row.account_alias == account.alias
        ]
        payloads = [(row.id, discovered_from_row(row)) for row in rows]
    finally:
        session.close()
    for _cluster_id, cluster in payloads:
        try:
            certificates.extend(_tls_certificates(factory, config, cluster))
        except Exception as error:
            logger.warning("ACK TLS certificate scan skipped cluster=%s error=%s", cluster.name, classify_alibaba_error(error))
    return certificates


def _tls_certificates(factory: AlibabaClientFactory, config, cluster: DiscoveredCluster) -> list[DiscoveredCertificate]:
    import json

    extra = {}
    try:
        extra = json.loads(cluster.extra_json or "{}")
    except Exception:
        extra = {}
    cluster_id = str(extra.get("cluster_id") or cluster.arn.rsplit("/", 1)[-1])
    payload = factory.describe_kubeconfig(cluster_id)
    kubeconfig_yaml = payload.get("config") or payload.get("kubeconfig") or ""
    if not kubeconfig_yaml:
        return []
    import yaml
    from kubernetes import client

    kubeconfig = yaml.safe_load(kubeconfig_yaml) if isinstance(kubeconfig_yaml, str) else kubeconfig_yaml
    if not isinstance(kubeconfig, dict):
        return []
    endpoint, token, _ca, _cert, _key = kubeconfig_auth_material(kubeconfig)
    if not endpoint:
        return []
    configuration = client.Configuration()
    configuration.host = endpoint
    configuration.verify_ssl = False
    if token:
        configuration.api_key = {"authorization": f"Bearer {token}"}
    core = client.CoreV1Api(client.ApiClient(configuration))
    secrets = core.list_secret_for_all_namespaces().items
    found: list[DiscoveredCertificate] = []
    ingress_hosts: dict[tuple[str, str], list[str]] = {}
    try:
        networking = client.NetworkingV1Api(client.ApiClient(configuration))
        ingress_hosts = ingress_secret_hosts(networking.list_ingress_for_all_namespaces().items)
    except Exception:
        ingress_hosts = {}
    for secret in secrets:
        payload = {
            "metadata": {"name": secret.metadata.name, "namespace": secret.metadata.namespace},
            "data": dict(secret.data or {}),
            "type": secret.type,
        }
        payload["data"].pop("tls.key", None)
        if payload["type"] != "kubernetes.io/tls":
            continue
        parsed = normalize_tls_secret(payload, config, cluster_name=cluster.name)
        if parsed is not None:
            parsed.environment = cluster.environment
            found.append(parsed)
    apply_ingress_usage(found, ingress_hosts)
    return found


def validate_account(account: AccountBinding) -> dict[str, str]:
    return ADAPTER.validate_account(account)


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
    logger.info("Alibaba discovery stored alias=%s count=%s", account.alias, len(clusters))
    return len(clusters)


def _store_health(account: AccountBinding, snapshots: list[tuple], repo: InventoryRepository) -> int:
    from app.services.health_sync import persist_account_health

    return persist_account_health(account, snapshots, repo)


def _store_certificates(account: AccountBinding, certificates: list[DiscoveredCertificate], repo: InventoryRepository) -> int:
    repo.replace_certificates_for_account(
        certificates,
        account_alias=account.alias,
        platform_region=account.logical_region,
    )
    return len(certificates)


def _store_validation(account: AccountBinding, identity: dict[str, str], repo: InventoryRepository) -> int:
    repo.mark_account_validated(account.id, fingerprint=identity["fingerprint"], status=identity["status"])
    for environment in account.environments:
        repo.mark_scope_success(environment_scope_id(account.alias, environment), "validation")
    return 1


def run_account_validation(job_id: str) -> int:
    accounts = accounts_for_job(job_id, "Alibaba")
    _mark_job_running(job_id)
    results = _run_bounded(accounts, validate_account, max(1, len(accounts) or 1))
    return _finish_fleet_job(job_id, kind="validation", results=results, persist=_store_validation)


def run_cluster_discovery(job_id: str) -> int:
    accounts = accounts_for_job(job_id, "Alibaba")
    _mark_job_running(job_id)
    results = _run_bounded(accounts, discover_account, max(1, len(accounts) or 1))
    return _finish_fleet_job(job_id, kind="discovery", results=results, persist=_store_discovery)


def run_health_scan(job_id: str) -> int:
    accounts = accounts_for_job(job_id, "Alibaba")
    _mark_job_running(job_id)
    clusters = _clusters_by_account(accounts)

    def collect(account: AccountBinding):
        return health_account(account, clusters.get(account.alias, []))

    results = _run_bounded(accounts, collect, max(1, len(accounts) or 1))
    return _finish_fleet_job(job_id, kind="health", results=results, persist=_store_health)


def run_certificate_scan(job_id: str) -> int:
    accounts = accounts_for_job(job_id, "Alibaba")
    _mark_job_running(job_id)
    results = _run_bounded(accounts, certificates_account, max(1, len(accounts) or 1))
    return _finish_fleet_job(job_id, kind="certificates", results=results, persist=_store_certificates)


def scan_alibaba_certificates() -> int:
    from app.services.aws_sync import persist_certificate_results

    accounts = accounts_for_job("", "Alibaba")
    results = _run_bounded(accounts, certificates_account, max(1, len(accounts) or 1))
    return persist_certificate_results(results)


def run_certificate_expiry_scan(job_id: str) -> int:
    from app.services.certificate_monitor import run_expiry_scan

    return run_expiry_scan(job_id)
