from __future__ import annotations

from app.domain.enums import Provider
from app.providers.aws.acm import AcmScanner
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.eks import EksDiscovery
from app.providers.aws.errors import AwsTransientError, classify_aws_error
from app.providers.aws.k8s import ClusterHealthCollector
from app.providers.common.models import DiscoveredCertificate, DiscoveredCluster
from app.providers.kubernetes.collector import inventory_payload
from app.topology.models import AccountBinding


class AWSProviderAdapter:
    """Live AWS inventory adapter. boto3 clients stay inside this package."""

    name: Provider = "AWS"

    def discover_clusters(self, account: AccountBinding) -> list[DiscoveredCluster]:
        config = account.connection_config()
        return EksDiscovery(AwsClientFactory(config=config), config).list_clusters(account.environments)

    def scan_health(
        self,
        account: AccountBinding,
        clusters: list[tuple[str, DiscoveredCluster]],
    ) -> list[tuple]:
        if not clusters:
            return []
        config = account.connection_config()
        factory = AwsClientFactory(config=config)
        discovery = EksDiscovery(factory, config)
        collector = ClusterHealthCollector(factory)
        snapshots: list[tuple] = []
        for cluster_id, cluster in clusters:
            try:
                raw = discovery.describe_raw(cluster.name)
                cluster.endpoint = raw.get("endpoint")
                ca_data = (raw.get("certificateAuthority") or {}).get("data")
                snapshot, resources = inventory_payload(collector, cluster, ca_data)
                snapshots.append((cluster_id, snapshot, resources))
            except Exception as error:
                mapped = classify_aws_error(error)
                if isinstance(mapped, AwsTransientError):
                    raise
                from app.core.logging import get_logger

                get_logger(__name__).warning("Health scan skipped cluster=%s error=%s", cluster.name, mapped)
        return snapshots

    def discover_certificates(self, account: AccountBinding) -> list[DiscoveredCertificate]:
        config = account.connection_config()
        return AcmScanner(AwsClientFactory(config=config), config).list_certificates()
