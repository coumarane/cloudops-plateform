from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AccountClass,
    AlertSeverity,
    ClusterStatus,
    Environment,
    FailureKind,
    HealthStatus,
    Platform,
    Provider,
    Region,
    RenewalStatus,
    RunResult,
    SecretAction,
    SecretRotationStatus,
)

HistoryResult = Literal["Succeeded", "Failed", "Cancelled"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scope(StrictModel):
    provider: Provider | None = None
    region: Region | None = None
    environment: Environment | None = None
    account: str | None = None


class ProviderRecord(StrictModel):
    id: Provider
    name: Provider
    platform: Platform
    regions: list[Region]


class RegionRecord(StrictModel):
    id: str
    name: Region
    provider: Provider
    cloudRegion: str
    platform: Platform


class AccountRecord(StrictModel):
    id: str
    account: str
    provider: Provider
    region: Region
    environment: Environment
    accountClass: AccountClass
    cloudRegion: str
    platform: Platform
    hostedEnvironments: list[Environment]
    environments: str
    clusters: int


class EnvironmentIdentity(StrictModel):
    provider: Provider
    region: Region
    environment: Environment
    platform: Platform
    cloudRegion: str
    account: str
    clusterName: str


class CellMetrics(StrictModel):
    clustersHealthy: int = 0
    clustersDegraded: int = 0
    clustersUnreachable: int = 0
    appsHealthy: int = 0
    appsDegraded: int = 0
    certsExpiring14d: int = 0
    nextCertExpiryDays: int | None = None
    secretsOverdue: int = 0
    secretsDueSoon: int = 0
    nextSecretDueDays: int | None = None
    failedDeploys: int = 0
    githubFailures: int = 0
    pipelineFailures: int = 0
    openAlerts: int = 0


class MatrixRow(StrictModel):
    provider: Provider
    platform: Platform
    region: Region
    cells: dict[Environment, CellMetrics]


class KpiSummary(StrictModel):
    clustersHealthy: int
    clustersDegraded: int
    clustersUnreachable: int
    appsHealthy: int
    appsDegraded: int
    certsExpiring14d: int
    secretsOverdue: int
    failedDeploys: int
    githubFailures: int
    pipelineFailures: int
    openAlerts: int


class OperationalAlert(StrictModel):
    id: str
    severity: AlertSeverity
    title: str
    objectName: str
    provider: Provider
    region: Region
    environment: Environment
    age: str
    href: str


class RecentFailure(StrictModel):
    id: str
    kind: FailureKind
    name: str
    provider: Provider
    region: Region
    environment: Environment
    age: str
    href: str


class ClusterRecord(StrictModel):
    id: str
    name: str
    platform: Platform
    version: str
    nodes: int
    provider: Provider
    region: Region
    environment: Environment
    account: str
    status: ClusterStatus
    appsLabel: str
    source: Literal["mock", "aws"] = "mock"
    awsAccountId: str | None = None
    cloudRegion: str | None = None
    endpointStatus: str | None = None
    clusterStatus: str | None = None
    platformVersion: str | None = None
    createdAt: str | None = None
    lastChecked: str | None = None


class ClusterHealthRecord(StrictModel):
    clusterId: str
    clusterName: str
    controlPlaneStatus: str
    kubernetesApiReachable: bool
    nodeCount: int
    readyNodeCount: int
    podCount: int
    unhealthyPodCount: int
    crashLoopBackOffCount: int
    pendingPodCount: int
    unavailableDeploymentCount: int
    failedJobCount: int
    lastChecked: str
    detail: str = ""
    status: ClusterStatus


class ApplicationRecord(StrictModel):
    id: str
    name: str
    namespace: str
    replicas: str
    issue: str
    provider: Provider
    region: Region
    environment: Environment
    cluster: str
    action: str = "Status"


class HealthCheckRecord(StrictModel):
    id: str
    name: str
    target: str
    checkType: str
    status: HealthStatus
    lastRun: str
    provider: Provider
    region: Region
    environment: Environment
    cluster: str


class RunRecord(StrictModel):
    id: str
    name: str
    detail: str
    result: RunResult
    age: str
    provider: Provider
    region: Region
    environment: Environment
    cluster: str
    source: Literal["mock", "aws"] = "mock"
    kind: str | None = None
    correlationId: str | None = None
    jobStatus: str | None = None


class AuditEvent(StrictModel):
    id: str
    event: str
    actor: str
    objectName: str
    detail: str
    age: str
    provider: Provider
    region: Region
    environment: Environment


class CertificateRecord(StrictModel):
    id: str
    name: str
    domain: str
    provider: Provider
    region: Region
    environment: Environment
    cluster: str
    namespace: str
    issuer: str
    expiresOn: str
    daysRemaining: int
    renewalStatus: RenewalStatus
    source: Literal["mock", "aws"] = "mock"
    arn: str | None = None
    subjectAlternativeNames: list[str] = Field(default_factory=list)
    status: str | None = None
    notBefore: str | None = None
    notAfter: str | None = None
    inUseBy: list[str] = Field(default_factory=list)
    renewalEligibility: str | None = None
    lastChecked: str | None = None


class SecretHistoryEvent(StrictModel):
    at: str
    actor: str
    action: SecretAction
    result: HistoryResult
    detail: str


class SecretRecord(StrictModel):
    id: str
    name: str
    namespace: str
    provider: Provider
    region: Region
    environment: Environment
    account: str
    status: SecretRotationStatus
    lastRotated: str
    nextDue: str
    lastValidated: str
    history: list[SecretHistoryEvent] = Field(default_factory=list)


class ActivityItem(StrictModel):
    title: str
    detail: str
    age: str


class EnvironmentCertificate(StrictModel):
    name: str
    daysToExpiry: int


class EnvironmentSecret(StrictModel):
    name: str
    namespace: str
    status: SecretRotationStatus
    detail: str


class EnvironmentAlert(StrictModel):
    title: str
    objectName: str
    age: str
    severity: AlertSeverity


class EnvironmentRecord(StrictModel):
    identity: EnvironmentIdentity
    clusters: list[ClusterRecord]
    applications: list[ApplicationRecord]
    secrets: list[EnvironmentSecret]
    certificates: list[EnvironmentCertificate]
    deployments: list[ActivityItem]
    pipelines: list[ActivityItem]
    github: list[ActivityItem]
    health: list[ActivityItem]
    audit: list[ActivityItem]
    alerts: list[EnvironmentAlert]
    recentActivity: list[ActivityItem]


class AdminUser(StrictModel):
    id: str
    user: str
    role: str
    scope: str
    lastActive: str


class AdminIntegration(StrictModel):
    id: str
    name: str
    status: Literal["Connected", "Degraded"]
    scope: str
    note: str


class ListResponse(StrictModel):
    items: list
    lastSynced: str


class DashboardResponse(StrictModel):
    lastSynced: str
    kpis: KpiSummary
    matrix: list[MatrixRow]
    alerts: list[OperationalAlert]
    failures: list[RecentFailure]
