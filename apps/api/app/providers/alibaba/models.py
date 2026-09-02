from dataclasses import dataclass

from app.providers.common.models import ClusterHealthSnapshot, DiscoveredCertificate, DiscoveredCluster


@dataclass(frozen=True)
class AlibabaConnectionConfig:
    cloud_region: str
    account_id: str | None
    role_arn: str | None
    session_name: str
    access_key_id_ref: str | None
    access_key_secret_ref: str | None
    credential_ref: str | None
    platform_region: str
    environment: str
    account_alias: str
    cluster_environment_tag: str
    environment_id: str = ""


@dataclass
class AlibabaIdentity:
    account_id: str
    arn: str
    fingerprint: str
    status: str


__all__ = [
    "AlibabaConnectionConfig",
    "AlibabaIdentity",
    "ClusterHealthSnapshot",
    "DiscoveredCertificate",
    "DiscoveredCluster",
]
