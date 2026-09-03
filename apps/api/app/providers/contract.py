from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.providers.common.models import DiscoveredCertificate, DiscoveredCluster
from app.topology.models import AccountBinding


@dataclass(frozen=True)
class ConnectionValidation:
    connected: bool
    account_id: str = ""
    principal: str = ""
    region: str = ""
    error_category: str = ""
    detail: str = ""


class CloudProviderAdapter(ABC):
    """Live provider operations used by administration and discovery."""

    provider_type: str
    discovery_job_kind: str
    health_job_kind: str
    certificate_job_kind: str

    @abstractmethod
    def validate_connection(self, account: AccountBinding) -> ConnectionValidation: ...

    @abstractmethod
    def discover_clusters(self, account: AccountBinding) -> list[DiscoveredCluster]: ...

    @abstractmethod
    def discover_certificates(self, account: AccountBinding) -> list[DiscoveredCertificate]: ...

    @abstractmethod
    def collect_health(self, account: AccountBinding, clusters: list[tuple[str, DiscoveredCluster]]) -> list[tuple]: ...
