from abc import ABC, abstractmethod

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


class CloudProviderPort(ABC):
    """Provider-specific inventory. Phase 2 adapters are mock-only."""

    name: Provider

    @abstractmethod
    def list_regions(self) -> list[RegionRecord]: ...

    @abstractmethod
    def list_accounts(self) -> list[AccountRecord]: ...

    @abstractmethod
    def list_environments(self) -> list[EnvironmentIdentity]: ...

    @abstractmethod
    def get_environment(self, region: Region, environment: Environment) -> EnvironmentRecord | None: ...

    @abstractmethod
    def list_clusters(self) -> list[ClusterRecord]: ...

    @abstractmethod
    def list_applications(self) -> list[ApplicationRecord]: ...

    @abstractmethod
    def list_certificates(self) -> list[CertificateRecord]: ...

    @abstractmethod
    def list_secrets(self) -> list[SecretRecord]: ...

    @abstractmethod
    def list_health_checks(self) -> list[HealthCheckRecord]: ...

    @abstractmethod
    def list_deployments(self) -> list[RunRecord]: ...

    @abstractmethod
    def list_pipelines(self) -> list[RunRecord]: ...

    @abstractmethod
    def list_jobs(self) -> list[RunRecord]: ...

    @abstractmethod
    def list_github_runs(self) -> list[RunRecord]: ...

    @abstractmethod
    def list_alerts(self) -> list[OperationalAlert]: ...

    @abstractmethod
    def list_audit_events(self) -> list[AuditEvent]: ...
