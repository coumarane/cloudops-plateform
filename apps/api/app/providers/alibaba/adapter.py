from __future__ import annotations

from app.domain.enums import Provider
from app.providers.alibaba.ack import AckDiscovery
from app.providers.alibaba.auth import get_caller_identity
from app.providers.alibaba.certificates import AlibabaCertificateScanner
from app.providers.alibaba.client import AlibabaClientFactory
from app.providers.alibaba.exceptions import AlibabaTransientError, classify_alibaba_error
from app.providers.alibaba.k8s import AckHealthCollector
from app.providers.common.models import DiscoveredCertificate, DiscoveredCluster
from app.providers.kubernetes.collector import inventory_payload
from app.topology.models import AccountBinding


class AlibabaProviderAdapter:
    """Live Alibaba inventory adapter. SDK objects stay inside this package."""

    name: Provider = "Alibaba"

    def validate_account(self, account: AccountBinding) -> dict[str, str]:
        identity = get_caller_identity(account.connection_config())
        return {"account_id": identity.account_id, "fingerprint": identity.fingerprint, "status": identity.status}

    def discover_clusters(self, account: AccountBinding) -> list[DiscoveredCluster]:
        config = account.connection_config()
        return AckDiscovery(AlibabaClientFactory(config), config).list_clusters(account.environments)

    def scan_health(
        self,
        account: AccountBinding,
        clusters: list[tuple[str, DiscoveredCluster]],
    ) -> list[tuple]:
        if not clusters:
            return []
        config = account.connection_config()
        collector = AckHealthCollector(AlibabaClientFactory(config), config)
        snapshots: list[tuple] = []
        for cluster_id, cluster in clusters:
            try:
                snapshot, resources = inventory_payload(collector, cluster)
                snapshots.append((cluster_id, snapshot, resources))
            except Exception as error:
                mapped = classify_alibaba_error(error)
                if isinstance(mapped, AlibabaTransientError):
                    raise
                from app.core.logging import get_logger

                get_logger(__name__).warning("Health scan skipped cluster=%s error=%s", cluster.name, mapped)
        return snapshots

    def discover_certificates(self, account: AccountBinding) -> list[DiscoveredCertificate]:
        config = account.connection_config()
        return AlibabaCertificateScanner(AlibabaClientFactory(config), config).list_certificates()
