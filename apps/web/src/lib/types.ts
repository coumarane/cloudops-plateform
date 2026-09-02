export const PROVIDERS = ["AWS", "Alibaba"] as const;
export type Provider = (typeof PROVIDERS)[number];

export const REGIONS = ["AMER", "EMEA", "APAC", "China"] as const;
export type Region = (typeof REGIONS)[number];

export const ENVIRONMENTS = ["DEV", "INT/TST", "UAT", "NPD", "PRD"] as const;
export type Environment = (typeof ENVIRONMENTS)[number];

export const NON_PRODUCTION_ENVIRONMENTS = ["DEV", "INT/TST", "UAT"] as const;
export const PRODUCTION_ENVIRONMENTS = ["NPD", "PRD"] as const;

export type ClusterPlatform = "EKS" | "ACK";
export type Severity = "healthy" | "warning" | "critical";
export type AlertSeverity = "critical" | "warning" | "info";
export type FailureKind = "deployment" | "github" | "pipeline";

export type ProviderFilter = "all" | Provider;
export type RegionFilter = "all" | Region;
export type EnvironmentFilter = "all" | Environment;

export type DashboardFilters = {
  provider: ProviderFilter;
  region: RegionFilter;
  environment: EnvironmentFilter;
};

export type CellMetrics = {
  clustersHealthy: number;
  clustersDegraded: number;
  clustersUnreachable: number;
  appsHealthy: number;
  appsDegraded: number;
  certsExpiring14d: number;
  certsHealthy?: number;
  certsExpiring60d?: number;
  certsExpiring30d?: number;
  certsExpiring7d?: number;
  certsExpired?: number;
  nextCertExpiryDays?: number;
  secretsOverdue: number;
  secretsDueSoon: number;
  nextSecretDueDays?: number;
  failedDeploys: number;
  githubFailures: number;
  pipelineFailures: number;
  openAlerts: number;
  live?: boolean;
  lastError?: string | null;
  readonly?: boolean;
};

export type MatrixRow = {
  provider: Provider;
  platform: ClusterPlatform;
  region: Region;
  cells: Record<Environment, CellMetrics>;
};

export type OperationalAlert = {
  id: string;
  severity: AlertSeverity;
  title: string;
  objectName: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  age: string;
  href: string;
};

export type RecentFailure = {
  id: string;
  kind: FailureKind;
  name: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  age: string;
  href: string;
};

export type KpiSummary = {
  clustersHealthy: number;
  clustersDegraded: number;
  clustersUnreachable: number;
  appsHealthy: number;
  appsDegraded: number;
  certsExpiring14d: number;
  certsHealthy?: number;
  certsExpiring60d?: number;
  certsExpiring30d?: number;
  certsExpiring7d?: number;
  certsExpired?: number;
  secretsOverdue: number;
  failedDeploys: number;
  githubFailures: number;
  githubWorkflowsRunning?: number;
  githubWorkflowsFailed?: number;
  githubWorkflowsSucceeded?: number;
  pipelineFailures: number;
  pipelineRunsToday?: number;
  pipelinesRunning?: number;
  pipelinesFailed?: number;
  pipelinesFailedPrd?: number;
  pipelineAverageDurationSeconds?: number;
  openAlerts: number;
};
