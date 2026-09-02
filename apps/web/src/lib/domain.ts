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
  source?: "mock" | "aws";
  awsAccountId?: string | null;
  cloudRegion?: string | null;
  endpointStatus?: string | null;
  clusterStatus?: string | null;
  platformVersion?: string | null;
  createdAt?: string | null;
  lastChecked?: string | null;
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
  source?: "mock" | "aws";
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
  status: "Connected" | "Degraded";
  scope: string;
  note: string;
};

export type SecretHistoryEvent = {
  at: string;
  actor: string;
  action: "Update" | "Rotate" | "Validate";
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
  source?: "mock" | "aws";
  arn?: string | null;
  subjectAlternativeNames?: string[];
  status?: string | null;
  notBefore?: string | null;
  notAfter?: string | null;
  inUseBy?: string[];
  renewalEligibility?: string | null;
  lastChecked?: string | null;
};

export type EnvironmentIdentity = {
  provider: Provider;
  region: Region;
  environment: Environment;
  platform: ClusterPlatform;
  cloudRegion: string;
  account: string;
  clusterName: string;
};

export type ActivityItem = {
  title: string;
  detail: string;
  age: string;
};

export type EnvironmentRecord = {
  identity: EnvironmentIdentity;
  lastSynced?: string;
  clusters: ClusterRecord[];
  applications: ApplicationRecord[];
  secrets: Array<{ name: string; namespace: string; status: SecretRecord["status"]; detail: string }>;
  certificates: Array<{ name: string; daysToExpiry: number }>;
  deployments: ActivityItem[];
  pipelines: ActivityItem[];
  github: ActivityItem[];
  health: ActivityItem[];
  audit: ActivityItem[];
  alerts: Array<{ title: string; objectName: string; age: string; severity: AlertSeverity }>;
  recentActivity: ActivityItem[];
};

export type DashboardSnapshot = {
  lastSynced: string;
  kpis: KpiSummary;
  matrix: MatrixRow[];
  alerts: OperationalAlert[];
  failures: RecentFailure[];
};
