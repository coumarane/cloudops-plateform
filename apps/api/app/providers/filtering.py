from typing import TYPE_CHECKING

from app.domain.enums import Environment, Provider, Region
from app.domain.models import (
    AccountRecord,
    ApplicationRecord,
    AuditEvent,
    CertificateRecord,
    ClusterRecord,
    EnvironmentIdentity,
    EnvironmentRecord,
    HealthCheckRecord,
    OperationalAlert,
    RegionRecord,
    RunRecord,
    SecretRecord,
)
from app.providers.base import CloudProviderPort

if TYPE_CHECKING:
    from app.data.inventory import MockInventory


class FilteringAdapter(CloudProviderPort):
    """Slices a shared mock inventory down to one cloud provider."""

    def __init__(self, name: Provider, inventory: "MockInventory") -> None:
        self.name = name
        self._inventory = inventory

    def list_regions(self) -> list[RegionRecord]:
        return [item for item in self._inventory.regions if item.provider == self.name]

    def list_accounts(self) -> list[AccountRecord]:
        return [item for item in self._inventory.accounts if item.provider == self.name]

    def list_environments(self) -> list[EnvironmentIdentity]:
        return [item for item in self._inventory.identities if item.provider == self.name]

    def get_environment(self, region: Region, environment: Environment) -> EnvironmentRecord | None:
        return self._inventory.environment_map.get((self.name, region, environment))

    def list_clusters(self) -> list[ClusterRecord]:
        return [item for item in self._inventory.clusters if item.provider == self.name]

    def list_applications(self) -> list[ApplicationRecord]:
        return [item for item in self._inventory.applications if item.provider == self.name]

    def list_certificates(self) -> list[CertificateRecord]:
        return [item for item in self._inventory.certificates if item.provider == self.name]

    def list_secrets(self) -> list[SecretRecord]:
        return [item for item in self._inventory.secrets if item.provider == self.name]

    def list_health_checks(self) -> list[HealthCheckRecord]:
        return [item for item in self._inventory.health_checks if item.provider == self.name]

    def list_deployments(self) -> list[RunRecord]:
        return [item for item in self._inventory.deployments if item.provider == self.name]

    def list_pipelines(self) -> list[RunRecord]:
        return [item for item in self._inventory.pipelines if item.provider == self.name]

    def list_jobs(self) -> list[RunRecord]:
        return [item for item in self._inventory.jobs if item.provider == self.name]

    def list_github_runs(self) -> list[RunRecord]:
        return [item for item in self._inventory.github_runs if item.provider == self.name]

    def list_alerts(self) -> list[OperationalAlert]:
        return [item for item in self._inventory.alerts if item.provider == self.name]

    def list_audit_events(self) -> list[AuditEvent]:
        return [item for item in self._inventory.audit_events if item.provider == self.name]
