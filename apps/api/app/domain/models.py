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
    readonly: bool = False
    source: Literal["mock", "aws", "alibaba"] = "mock"
    lastSuccessfulScan: str | None = None
    lastError: str | None = None
    discoveryActive: bool = False
    awsAccountId: str | None = None
    certificateStatus: str | None = None
    certificateTotal: int | None = None
    certificateWarning: int | None = None
    certificateCritical: int | None = None
    overallHealth: str | None = None
    appsTotal: int | None = None
    appsHealthyCount: int | None = None
    appsDegradedCount: int | None = None
    appsUnhealthyCount: int | None = None
    appsCriticalCount: int | None = None
    openIncidents: int | None = None
    pipelinesFailedRecently: int | None = None


class CellMetrics(StrictModel):
    clustersHealthy: int = 0
    clustersDegraded: int = 0
    clustersUnreachable: int = 0
    appsHealthy: int = 0
    appsDegraded: int = 0
    appsUnhealthy: int = 0
    appsCritical: int = 0
    certsExpiring14d: int = 0
    certsHealthy: int = 0
    certsExpiring60d: int = 0
    certsExpiring30d: int = 0
    certsExpiring7d: int = 0
    certsExpired: int = 0
    nextCertExpiryDays: int | None = None
    secretsOverdue: int = 0
    secretsDueSoon: int = 0
    nextSecretDueDays: int | None = None
    failedDeploys: int = 0
    githubFailures: int = 0
    pipelineFailures: int = 0
    openAlerts: int = 0
    openIncidents: int = 0
    live: bool = False
    lastError: str | None = None
    readonly: bool = False


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
    appsUnhealthy: int = 0
    appsCritical: int = 0
    certsExpiring14d: int
    certsHealthy: int = 0
    certsExpiring60d: int = 0
    certsExpiring30d: int = 0
    certsExpiring7d: int = 0
    certsExpired: int = 0
    secretsOverdue: int
    failedDeploys: int
    githubFailures: int
    githubWorkflowsRunning: int = 0
    githubWorkflowsFailed: int = 0
    githubWorkflowsSucceeded: int = 0
    pipelineFailures: int
    pipelineRunsToday: int = 0
    pipelinesRunning: int = 0
    pipelinesFailed: int = 0
    pipelinesFailedPrd: int = 0
    pipelineAverageDurationSeconds: int = 0
    openAlerts: int
    openIncidents: int = 0
    unhealthyClusters: int = 0
    criticalAlerts: int = 0
    prdCriticalAlerts: int = 0
    acknowledgedAlerts: int = 0


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
    source: Literal["mock", "aws", "alibaba"] = "mock"
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
    statefulSetUnhealthyCount: int = 0
    ingressUnhealthyCount: int = 0
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
    repositoryId: str | None = None
    repository: str | None = None
    branch: str | None = None
    commitSha: str | None = None
    workflow: str | None = None
    latestWorkflowStatus: str | None = None
    latestDeploymentStatus: str | None = None
    sourceEnvironment: str | None = None
    workflowRunId: str | None = None
    deploymentId: str | None = None
    pipelineId: str | None = None
    pipelineName: str | None = None
    pipelineProvider: str | None = None
    latestPipelineRunId: str | None = None
    latestPipelineStatus: str | None = None
    healthStatus: str | None = None
    healthSummary: str | None = None
    likelyCause: str | None = None


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
    source: Literal["mock", "aws", "alibaba", "github"] = "mock"
    kind: str | None = None
    correlationId: str | None = None
    jobStatus: str | None = None
    href: str | None = None


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
    source: str = "mock"
    arn: str | None = None
    subjectAlternativeNames: list[str] = Field(default_factory=list)
    status: str | None = None
    notBefore: str | None = None
    notAfter: str | None = None
    inUseBy: list[str] = Field(default_factory=list)
    renewalEligibility: str | None = None
    lastChecked: str | None = None
    account: str = ""
    expiryStatus: str = ""
    alertStatus: str | None = None
    serialNumber: str | None = None
    autoRenew: bool = False
    discoveryStatus: str | None = None
    lastSeenAt: str | None = None
    firstSeenAt: str | None = None
    clusterId: str | None = None
    applicationId: str | None = None
    handshakeOk: bool | None = None
    handshakeLatencyMs: int | None = None


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
    credentialType: str | None = None
    secretBackend: str | None = None
    fingerprint: str | None = None
    updatedBy: str | None = None
    lifecycleStatus: str | None = None
    source: Literal["mock", "live"] = "mock"
    maskedValue: str = "••••••••••••"


class CredentialRecord(StrictModel):
    id: str
    name: str
    provider: Provider
    region: Region
    account: str
    environment: Environment
    accountId: str = ""
    environmentId: str = ""
    credentialType: str
    secretBackend: str
    secretReference: str
    fingerprint: str
    status: str
    lastValidatedAt: str | None = None
    lastRotatedAt: str | None = None
    rotationDueAt: str | None = None
    rotationPolicyDays: int = 90
    createdAt: str
    updatedAt: str
    updatedBy: str
    roleArn: str = ""
    externalIdRef: str = ""
    cloudRegion: str = ""
    maskedValue: str = "••••••••••••"


class CredentialValidationRecord(StrictModel):
    id: str
    credentialId: str
    success: bool
    status: str
    latencyMs: int
    errorCategory: str
    providerAccount: str
    correlationId: str
    createdAt: str


class CredentialHistoryEvent(StrictModel):
    id: str
    action: str
    result: str
    detail: str
    actor: str
    createdAt: str


class ActivityItem(StrictModel):
    title: str
    detail: str
    age: str
    href: str | None = None


class CertificateHistoryEvent(StrictModel):
    id: str
    event: str
    detail: str
    createdAt: str


class CertificateAlertRecord(StrictModel):
    id: str
    certificateId: str
    kind: str
    severity: str
    status: str
    domain: str
    provider: str
    region: str
    account: str
    environment: str
    cluster: str
    expiresAt: str | None = None
    daysRemaining: int | None = None
    createdAt: str
    lastEvaluatedAt: str
    acknowledgedAt: str | None = None
    resolvedAt: str | None = None


class CertificateValidationEvent(StrictModel):
    id: str
    hostname: str
    handshakeOk: bool
    latencyMs: int
    issuer: str
    expiresAt: str | None = None
    error: str
    checkedAt: str


class EnvironmentCertificate(StrictModel):
    name: str
    daysToExpiry: int
    status: str = ""
    source: str = ""
    issuer: str = ""


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


class EnvironmentAlertsSummary(StrictModel):
    openAlerts: int = 0
    criticalAlerts: int = 0
    highAlerts: int = 0
    acknowledgedAlerts: int = 0


class EnvironmentMaintenanceWindow(StrictModel):
    id: str
    name: str
    startsAt: str
    endsAt: str
    reason: str = ""
    changeTicket: str = ""


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
    alertsSummary: EnvironmentAlertsSummary | None = None
    maintenanceWindow: EnvironmentMaintenanceWindow | None = None


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
