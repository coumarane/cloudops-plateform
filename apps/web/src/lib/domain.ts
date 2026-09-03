import type {
  AlertSeverity,
  ClusterPlatform,
  Environment,
  KpiSummary,
  MatrixRow,
  OperationalAlert,
  Provider,
  RecentFailure,
  Region,
} from "@/lib/types";

export type {
  AlertSeverity,
  CellMetrics,
  ClusterPlatform,
  Environment,
  KpiSummary,
  MatrixRow,
  OperationalAlert,
  Provider,
  RecentFailure,
  Region,
} from "@/lib/types";

export type ProviderRecord = {
  id: Provider;
  name: Provider;
  platform: ClusterPlatform;
  regions: Region[];
};

export type RegionRecord = {
  id: string;
  name: Region;
  provider: Provider;
  cloudRegion: string;
  platform: ClusterPlatform;
};

export type AccountRecord = {
  id: string;
  account: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  accountClass: "Production" | "Non-production";
  cloudRegion: string;
  platform: ClusterPlatform;
  hostedEnvironments: Environment[];
  environments: string;
  clusters: number;
};

export type ClusterRecord = {
  id: string;
  name: string;
  platform: ClusterPlatform;
  version: string;
  nodes: number;
  provider: Provider;
  region: Region;
  environment: Environment;
  account: string;
  status: "Healthy" | "Degraded" | "Unreachable";
  appsLabel: string;
  source?: "mock" | "aws" | "alibaba";
  awsAccountId?: string | null;
  cloudRegion?: string | null;
  endpointStatus?: string | null;
  clusterStatus?: string | null;
  platformVersion?: string | null;
  createdAt?: string | null;
  lastChecked?: string | null;
  ignored?: boolean;
  monitoringEnabled?: boolean;
  externalClusterId?: string | null;
};

export type ClusterHealthRecord = {
  clusterId: string;
  clusterName: string;
  controlPlaneStatus: string;
  kubernetesApiReachable: boolean;
  nodeCount: number;
  readyNodeCount: number;
  podCount: number;
  unhealthyPodCount: number;
  crashLoopBackOffCount: number;
  pendingPodCount: number;
  unavailableDeploymentCount: number;
  failedJobCount: number;
  statefulSetUnhealthyCount?: number;
  ingressUnhealthyCount?: number;
  lastChecked: string;
  detail: string;
  status: "Healthy" | "Degraded" | "Unreachable";
};

export type ApplicationRecord = {
  id: string;
  name: string;
  namespace: string;
  replicas: string;
  issue: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  cluster: string;
  action?: string;
  repositoryId?: string | null;
  repository?: string | null;
  branch?: string | null;
  commitSha?: string | null;
  workflow?: string | null;
  latestWorkflowStatus?: string | null;
  latestDeploymentStatus?: string | null;
  sourceEnvironment?: string | null;
  workflowRunId?: string | null;
  deploymentId?: string | null;
  pipelineId?: string | null;
  pipelineName?: string | null;
  pipelineProvider?: string | null;
  latestPipelineRunId?: string | null;
  latestPipelineStatus?: string | null;
  healthStatus?: string | null;
  healthSummary?: string | null;
  likelyCause?: string | null;
};

export type HealthCheckRecord = {
  id: string;
  name: string;
  target: string;
  checkType: string;
  status: "Passing" | "Warning" | "Failing";
  lastRun: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  cluster: string;
};

export type RunRecord = {
  id: string;
  name: string;
  detail: string;
  result: "Succeeded" | "Failed" | "Running";
  age: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  cluster: string;
  source?: "mock" | "aws" | "alibaba";
  kind?: string | null;
  correlationId?: string | null;
  jobStatus?: string | null;
};

export type AuditEvent = {
  id: string;
  event: string;
  actor: string;
  objectName: string;
  detail: string;
  age: string;
  provider: Provider;
  region: Region;
  environment: Environment;
};

export type AdminUser = {
  id: string;
  user: string;
  role: string;
  scope: string;
  lastActive: string;
};

export type AdminIntegration = {
  id: string;
  name: string;
  status: string;
  scope: string;
  note: string;
  type?: string;
  enabled?: boolean;
};

export type SecretHistoryEvent = {
  at: string;
  actor: string;
  action: "Update" | "Rotate" | "Validate" | "Replace";
  result: "Succeeded" | "Failed" | "Cancelled";
  detail: string;
};

export type SecretRecord = {
  id: string;
  name: string;
  namespace: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  account: string;
  status: "OK" | "Overdue" | "Due soon";
  lastRotated: string;
  nextDue: string;
  lastValidated: string;
  history: SecretHistoryEvent[];
  credentialType?: string | null;
  secretBackend?: string | null;
  fingerprint?: string | null;
  updatedBy?: string | null;
  lifecycleStatus?: string | null;
  source?: "mock" | "live";
  maskedValue?: string;
  keys?: string[];
  arn?: string | null;
  description?: string | null;
  kmsKeyId?: string | null;
  cloudRegion?: string | null;
};

export type CredentialRecord = {
  id: string;
  name: string;
  provider: Provider;
  region: Region;
  account: string;
  environment: Environment;
  accountId?: string;
  environmentId?: string;
  credentialType: string;
  secretBackend: string;
  secretReference: string;
  fingerprint: string;
  status: string;
  lastValidatedAt?: string | null;
  lastRotatedAt?: string | null;
  rotationDueAt?: string | null;
  rotationPolicyDays?: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string;
  roleArn?: string;
  externalIdRef?: string;
  cloudRegion?: string;
  maskedValue?: string;
};

export type CredentialHistoryEvent = {
  id: string;
  action: string;
  result: string;
  detail: string;
  actor: string;
  createdAt: string;
};

export type CertificateRecord = {
  id: string;
  name: string;
  domain: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  cluster: string;
  namespace: string;
  issuer: string;
  expiresOn: string;
  daysRemaining: number;
  renewalStatus: "OK" | "Expiring" | "Renewing" | "Expired";
  source?: string;
  arn?: string | null;
  subjectAlternativeNames?: string[];
  status?: string | null;
  notBefore?: string | null;
  notAfter?: string | null;
  inUseBy?: string[];
  renewalEligibility?: string | null;
  lastChecked?: string | null;
  account?: string;
  expiryStatus?: string;
  alertStatus?: string | null;
  serialNumber?: string | null;
  autoRenew?: boolean;
  discoveryStatus?: string | null;
  lastSeenAt?: string | null;
  firstSeenAt?: string | null;
  clusterId?: string | null;
  applicationId?: string | null;
  handshakeOk?: boolean | null;
  handshakeLatencyMs?: number | null;
  history?: Array<{ id: string; event: string; detail: string; createdAt: string }>;
  alerts?: Array<{ id: string; kind: string; severity: string; status: string; domain: string }>;
  validations?: Array<{ id: string; hostname: string; handshakeOk: boolean; latencyMs: number; checkedAt: string }>;
};

export type EnvironmentIdentity = {
  id?: string | null;
  readiness?: string | null;
  provider: Provider;
  region: Region;
  environment: Environment;
  platform: ClusterPlatform;
  cloudRegion: string;
  account: string;
  clusterName: string;
  source?: "mock" | "aws" | "alibaba";
  lastSuccessfulScan?: string | null;
  lastError?: string | null;
  discoveryActive?: boolean;
  readonly?: boolean;
  awsAccountId?: string | null;
  certificateStatus?: string | null;
  certificateTotal?: number | null;
  certificateWarning?: number | null;
  certificateCritical?: number | null;
  overallHealth?: string | null;
  appsTotal?: number | null;
  appsHealthyCount?: number | null;
  appsDegradedCount?: number | null;
  appsUnhealthyCount?: number | null;
  appsCriticalCount?: number | null;
  openIncidents?: number | null;
  pipelinesFailedRecently?: number | null;
};

export type ActivityItem = {
  title: string;
  detail: string;
  age: string;
  href?: string | null;
};

export type EnvironmentRecord = {
  identity: EnvironmentIdentity;
  lastSynced?: string;
  clusters: ClusterRecord[];
  applications: ApplicationRecord[];
  secrets: Array<{ name: string; namespace: string; status: SecretRecord["status"]; detail: string }>;
  certificates: Array<{ name: string; daysToExpiry: number; status?: string; source?: string; issuer?: string }>;
  deployments: ActivityItem[];
  pipelines: ActivityItem[];
  github: ActivityItem[];
  health: ActivityItem[];
  audit: ActivityItem[];
  alerts: Array<{ title: string; objectName: string; age: string; severity: AlertSeverity }>;
  recentActivity: ActivityItem[];
  alertsSummary?: {
    openAlerts: number;
    criticalAlerts: number;
    highAlerts: number;
    acknowledgedAlerts: number;
  } | null;
  maintenanceWindow?: {
    id: string;
    name: string;
    startsAt: string;
    endsAt: string;
    reason: string;
    changeTicket: string;
  } | null;
};

export type DashboardSnapshot = {
  lastSynced: string;
  kpis: KpiSummary;
  matrix: MatrixRow[];
  alerts: OperationalAlert[];
  failures: RecentFailure[];
  demoMode?: boolean;
  dataSource?: string;
  onboarding?: boolean;
  configuredProviders?: number;
};
