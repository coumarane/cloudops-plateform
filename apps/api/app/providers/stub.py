from __future__ import annotations

from datetime import datetime, timezone

from app.providers.common.models import DiscoveredCertificate, DiscoveredCluster
from app.providers.contract import CloudProviderAdapter, ConnectionValidation
from app.topology.models import AccountBinding


class StubCloudProviderAdapter(CloudProviderAdapter):
    """Deterministic adapter for local/E2E flows when live credentials are unavailable."""

    def __init__(self, provider_type: str) -> None:
        self.provider_type = provider_type
        if provider_type == "Alibaba":
            self.discovery_job_kind = "alibaba-cluster-discovery"
            self.health_job_kind = "alibaba-health-scan"
            self.certificate_job_kind = "alibaba-certificate-discovery"
        else:
            self.discovery_job_kind = "aws-cluster-discovery"
            self.health_job_kind = "aws-health-scan"
            self.certificate_job_kind = "aws-certificate-scan"

    def validate_connection(self, account: AccountBinding) -> ConnectionValidation:
        return ConnectionValidation(
            connected=True,
            account_id=account.account_id or "123456789012",
            principal="CloudOpsRole",
            region=account.cloud_region,
        )

    def discover_clusters(self, account: AccountBinding) -> list[DiscoveredCluster]:
        environment = account.environments[0] if account.environments else "DEV"
        suffix = "ack" if self.provider_type == "Alibaba" else "eks"
        name = f"{account.alias}-{environment.lower()}-{suffix}"
        return [
            DiscoveredCluster(
                name=name,
                arn=f"arn:cloudops:{account.cloud_region}:{account.account_id or '123456789012'}:cluster/{name}",
                cloud_region=account.cloud_region,
                aws_account_id=account.account_id or "123456789012",
                kubernetes_version="1.31",
                endpoint_status="PRIVATE",
                cluster_status="ACTIVE",
                platform_version="stub.1",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                endpoint=f"https://{name}.example.internal",
                environment=environment,
                platform_region=account.logical_region,
                account_alias=account.alias,
                environment_id=account.environment_ids().get(environment, ""),
                provider=self.provider_type,
                cluster_type="EKS" if self.provider_type == "AWS" else "ACK",
            )
        ]

    def discover_certificates(self, account: AccountBinding) -> list[DiscoveredCertificate]:
        environment = account.environments[0] if account.environments else "DEV"
        return [
            DiscoveredCertificate(
                arn=f"arn:cloudops:acm:{account.cloud_region}:{account.account_id or '123456789012'}:certificate/stub",
                domain_name=f"*.{account.alias}.example",
                subject_alternative_names=[f"*.{account.alias}.example"],
                issuer="CloudOps Stub CA",
                status="ISSUED",
                not_before=datetime(2026, 1, 1, tzinfo=timezone.utc),
                not_after=datetime(2027, 1, 1, tzinfo=timezone.utc),
                days_remaining=120,
                in_use_by=[],
                renewal_eligibility="ELIGIBLE",
                environment=environment,
                platform_region=account.logical_region,
                account_alias=account.alias,
                cloud_region=account.cloud_region,
                environment_id=account.environment_ids().get(environment, ""),
                provider=self.provider_type,
                source="stub",
            )
        ]

    def collect_health(self, account: AccountBinding, clusters: list[tuple[str, DiscoveredCluster]]) -> list[tuple]:
        from app.providers.common.models import ClusterHealthSnapshot

        snapshots: list[tuple] = []
        now = datetime.now(timezone.utc)
        for cluster_id, cluster in clusters:
            snapshot = ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status="ACTIVE",
                kubernetes_api_reachable=True,
                node_count=3,
                ready_node_count=3,
                pod_count=12,
                last_checked=now,
                detail="stub health",
            )
            snapshots.append((cluster_id, snapshot, []))
        return snapshots
