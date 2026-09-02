import type { Environment, Provider, Region } from "@/lib/types";

export type HealthStatus = "HEALTHY" | "DEGRADED" | "UNHEALTHY" | "CRITICAL" | "UNKNOWN";

export type HealthOverview = {
  healthyApplications: number;
  degradedApplications: number;
  unhealthyApplications: number;
  criticalApplications: number;
  unknownApplications: number;
  unhealthyClusters: number;
  openIncidents: number;
  applications: number;
  lastSynced: string;
};

export type HealthResource = {
  id: string;
  resourceType: string;
  name: string;
  namespace: string;
  clusterId: string;
  applicationId: string;
  status: HealthStatus | string;
  summary: string;
  checkType: string;
  errorCategory: string;
  desired: number;
  ready: number;
  available: number;
  unavailable: number;
  restartCount: number;
  reason: string;
  provider?: string;
  region?: string;
  environment?: string;
  lastCheckedAt?: string | null;
};

export type HealthApplication = {
  id: string;
  applicationId: string;
  name: string;
  status: HealthStatus | string;
  summary: string;
  likelyCause: string;
  evidence: string[];
  correlation: {
    windowMinutes?: number;
    pipelineRuns?: Array<{ id: string; status: string; commitSha: string; startedAt?: string | null; externalRunId?: string }>;
    certificates?: Array<{ id: string; domain: string; status: string }>;
  };
  workload?: HealthResource | null;
  pods: HealthResource[];
  ingress?: HealthResource | null;
  endpoint?: HealthResource | null;
  certificateStatus: string;
  latestDeployment: { status: string; runId?: string; commitSha?: string; startedAt?: string | null };
  latestPipelineRun?: { id: string; status: string; commitSha: string; externalRunId?: string } | null;
  desiredReplicas: number;
  availableReplicas: number;
  crashloop: number;
  failedPods: number;
  restartCount: number;
  provider?: Provider | string;
  region?: Region | string;
  environment?: Environment | string;
  clusterId: string;
  resources: HealthResource[];
  lastAttemptedAt?: string | null;
  lastSuccessfulAt?: string | null;
  errorCategory?: string;
};

export type HealthIncident = {
  id: string;
  applicationId: string;
  status: string;
  severity: string;
  rootSymptom: string;
  openedAt?: string | null;
  acknowledgedAt?: string | null;
  resolvedAt?: string | null;
  age?: string;
  provider?: string;
  region?: string;
  environment?: string;
};

export type HealthTimelineEvent = {
  id: string;
  eventType: string;
  title: string;
  detail: string;
  href: string;
  createdAt?: string | null;
};

export type HealthFilters = {
  provider?: string;
  region?: string;
  environment?: string;
  app?: string;
  incident?: string;
  tab?: string;
  cluster?: string;
};

export function parseHealthFilters(search: Record<string, string | undefined>): HealthFilters {
  return {
    provider: search.provider,
    region: search.region,
    environment: search.environment,
    app: search.app,
    incident: search.incident,
    tab: search.tab,
    cluster: search.cluster,
  };
}

export function healthHref(filters: HealthFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/health-checks?${query}` : "/health-checks";
}

export function healthTone(status: string): "healthy" | "warning" | "critical" | "muted" {
  const key = status.toLowerCase();
  if (key === "healthy" || key === "passing") return "healthy";
  if (key === "degraded" || key === "warning") return "warning";
  if (key === "unhealthy" || key === "critical" || key === "failing") return "critical";
  return "muted";
}
