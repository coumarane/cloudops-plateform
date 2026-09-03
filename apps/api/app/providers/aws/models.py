from dataclasses import dataclass

from app.providers.common.models import ClusterHealthSnapshot, DiscoveredCertificate, DiscoveredCluster


@dataclass(frozen=True)
class AwsConnectionConfig:
    cloud_region: str
    account_id: str | None
    role_arn: str | None
    external_id: str | None
    session_name: str
    profile: str | None
    config_secret_arn: str | None
    platform_region: str
    environment: str
    account_alias: str
    cluster_environment_tag: str
    environment_id: str = ""
    credential_ref: str | None = None


__all__ = [
    "AwsConnectionConfig",
    "ClusterHealthSnapshot",
    "DiscoveredCertificate",
    "DiscoveredCluster",
]
