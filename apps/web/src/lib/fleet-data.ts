import { assertNoSecretValues, isProductionEnvironment } from "./dashboard";
import { catalogHref, matchesCatalogFilters } from "./catalog";
import {
  getEnvironmentIdentity,
  getEnvironmentRecord,
  listEnvironmentIdentities,
  type EnvironmentIdentity,
} from "./environment-data";
import { OPERATIONAL_ALERTS } from "./mock-data";
import type { AlertSeverity, Environment, Provider, Region } from "./types";

export type ScopeFilters = {
  provider: Provider | "all";
  region: Region | "all";
  environment: Environment | "all";
};

export type InfrastructureAccount = {
  id: string;
  account: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  accountClass: "Production" | "Non-production";
  cloudRegion: string;
  platform: "EKS" | "ACK";
  hostedEnvironments: Environment[];
  environments: string;
  clusters: number;
};

export type FleetCluster = {
  id: string;
  name: string;
  platform: "EKS" | "ACK";
  version: string;
  nodes: number;
  provider: Provider;
  region: Region;
  environment: Environment;
  account: string;
  status: "Healthy" | "Degraded" | "Unreachable";
  appsLabel: string;
};

export type FleetApplication = {
  id: string;
  name: string;
  namespace: string;
  replicas: string;
  issue: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  cluster: string;
};

export type FleetHealthCheck = {
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

export type FleetRun = {
  id: string;
  name: string;
  detail: string;
  result: "Succeeded" | "Failed" | "Running";
  age: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  cluster: string;
};

export type FleetAlert = {
  id: string;
  severity: AlertSeverity;
  title: string;
  objectName: string;
  age: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  href: string;
};

export type FleetAuditEvent = {
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

function identities(): EnvironmentIdentity[] {
  return listEnvironmentIdentities();
}

function recordFor(identity: EnvironmentIdentity) {
  return getEnvironmentRecord(identity.provider, identity.region, identity.environment);
}

export const INFRASTRUCTURE_ACCOUNTS: InfrastructureAccount[] = (() => {
  const seen = new Map<string, InfrastructureAccount>();
  for (const identity of identities()) {
    const key = `${identity.provider}-${identity.region}-${identity.account}`;
    const existing = seen.get(key);
    const production = isProductionEnvironment(identity.environment);
    if (!existing) {
      seen.set(key, {
        id: key,
        account: identity.account,
        provider: identity.provider,
        region: identity.region,
        environment: identity.environment,
        accountClass: production ? "Production" : "Non-production",
        cloudRegion: identity.cloudRegion,
        platform: identity.platform,
        hostedEnvironments: [identity.environment],
        environments: production ? "NPD · PRD" : "DEV · INT/TST · UAT",
        clusters: 1,
      });
    } else {
      existing.clusters += 1;
      if (!existing.hostedEnvironments.includes(identity.environment)) {
        existing.hostedEnvironments.push(identity.environment);
      }
    }
  }
  return Array.from(seen.values());
})();

export const FLEET_CLUSTERS: FleetCluster[] = identities().flatMap((identity) => {
  const record = recordFor(identity);
  return record.clusters.map((cluster) => ({
    id: cluster.name,
    name: cluster.name,
    platform: cluster.platform,
    version: cluster.version,
    nodes: cluster.nodes,
    provider: identity.provider,
    region: identity.region,
    environment: identity.environment,
    account: identity.account,
    status: cluster.status,
    appsLabel: cluster.appsLabel,
  }));
});

const EXTRA_APPLICATIONS: FleetApplication[] = [
  {
    id: "app-apac-prd-payment",
    name: "payment-svc",
    namespace: "prd",
    replicas: "0/3",
    issue: "Rollout aborted",
    ...scope("AWS", "APAC", "PRD"),
  },
  {
    id: "app-china-uat-gateway",
    name: "api-gateway-v2",
    namespace: "uat",
    replicas: "1/2",
    issue: "Restart loop",
    ...scope("Alibaba", "China", "UAT"),
  },
];

export const FLEET_APPLICATIONS: FleetApplication[] = [
  ...identities().flatMap((identity) => {
    const record = recordFor(identity);
    return record.applications.map((application) => ({
      id: `app-${identity.provider}-${identity.region}-${identity.environment}-${application.name}`,
      name: application.name,
      namespace: application.namespace,
      replicas: application.replicas,
      issue: application.issue,
      provider: identity.provider,
      region: identity.region,
      environment: identity.environment,
      cluster: identity.clusterName,
    }));
  }),
  ...EXTRA_APPLICATIONS,
];

export const FLEET_HEALTH_CHECKS: FleetHealthCheck[] = identities().flatMap((identity) => {
  const record = recordFor(identity);
  const cluster = record.clusters[0];
  const failing = cluster?.status === "Unreachable";
  const warning = cluster?.status === "Degraded";
  const rows: FleetHealthCheck[] = [
    {
      id: `hc-${identity.clusterName}-apiserver`,
      name: "kube-apiserver",
      target: identity.clusterName,
      checkType: "API probe",
      status: failing ? "Failing" : warning ? "Warning" : "Passing",
      lastRun: failing ? "10m ago" : "2m ago",
      provider: identity.provider,
      region: identity.region,
      environment: identity.environment,
      cluster: identity.clusterName,
    },
  ];
  if (identity.provider === "Alibaba" && identity.environment === "UAT") {
    rows.push({
      id: "hc-china-uat-prometheus",
      name: "prometheus-server",
      target: "prometheus-server",
      checkType: "Memory",
      status: "Warning",
      lastRun: "2h ago",
      provider: "Alibaba",
      region: "China",
      environment: "UAT",
      cluster: identity.clusterName,
    });
  }
  return rows;
});

export const FLEET_DEPLOYMENTS: FleetRun[] = identities().map((identity) => {
  const record = recordFor(identity);
  const failed = record.deployments.some((item) => /fail/i.test(item.title));
  const activity = record.deployments[0];
  return {
    id: `dep-${identity.clusterName}`,
    name: failed ? "payment-svc" : "platform-api",
    detail: activity?.detail ?? "Rollout complete",
    result: failed ? "Failed" : "Succeeded",
    age: activity?.age ?? "2h ago",
    provider: identity.provider,
    region: identity.region,
    environment: identity.environment,
    cluster: identity.clusterName,
  };
});

export const FLEET_PIPELINES: FleetRun[] = identities().map((identity) => {
  const record = recordFor(identity);
  const failed = record.pipelines.some((item) => /fail/i.test(item.title));
  const activity = record.pipelines[0];
  return {
    id: `pipe-${identity.clusterName}`,
    name: failed ? "data-sync" : "env-sync",
    detail: activity?.detail ?? "Last green run",
    result: failed ? "Failed" : "Succeeded",
    age: activity?.age ?? "6h ago",
    provider: identity.provider,
    region: identity.region,
    environment: identity.environment,
    cluster: identity.clusterName,
  };
});

export const FLEET_GITHUB_RUNS: FleetRun[] = identities().map((identity) => {
  const record = recordFor(identity);
  const failed = record.github.some((item) => /fail/i.test(item.title));
  const activity = record.github[0];
  const repo =
    identity.provider === "Alibaba" ? "cloudops/ack-platform" : "cloudops/eks-platform";
  return {
    id: `gh-${identity.clusterName}`,
    name: failed ? "auth-build" : "ci-verify",
    detail: repo,
    result: failed ? "Failed" : "Succeeded",
    age: activity?.age ?? "4h ago",
    provider: identity.provider,
    region: identity.region,
    environment: identity.environment,
    cluster: identity.clusterName,
  };
});

export const FLEET_JOBS: FleetRun[] = [
  {
    id: "job-amer-prd-cert-scan",
    name: "cert-expiry-scanner",
    detail: "Scheduled",
    result: "Succeeded",
    age: "1h ago",
    ...scope("AWS", "AMER", "PRD"),
  },
  {
    id: "job-emea-uat-backup",
    name: "nightly-db-backup",
    detail: "Scheduled",
    result: "Succeeded",
    age: "4h ago",
    ...scope("AWS", "EMEA", "UAT"),
  },
  {
    id: "job-emea-npd-sync",
    name: "data-sync-job",
    detail: "Scheduled",
    result: "Failed",
    age: "2h ago",
    ...scope("AWS", "EMEA", "NPD"),
  },
  {
    id: "job-apac-int-gc",
    name: "image-gc",
    detail: "Scheduled",
    result: "Succeeded",
    age: "6h ago",
    ...scope("AWS", "APAC", "INT/TST"),
  },
  {
    id: "job-china-uat-logs",
    name: "ack-log-shipper",
    detail: "Scheduled",
    result: "Succeeded",
    age: "3h ago",
    ...scope("Alibaba", "China", "UAT"),
  },
  {
    id: "job-amer-dev-lint",
    name: "policy-lint",
    detail: "Scheduled",
    result: "Succeeded",
    age: "8h ago",
    ...scope("AWS", "AMER", "DEV"),
  },
];

export const FLEET_ALERTS: FleetAlert[] = [
  ...OPERATIONAL_ALERTS.map((alert) => ({
    id: alert.id,
    severity: alert.severity,
    title: alert.title,
    objectName: alert.objectName,
    age: alert.age,
    provider: alert.provider,
    region: alert.region,
    environment: alert.environment,
    href: alert.href,
  })),
  {
    id: "alert-apac-prd-deploy",
    severity: "critical",
    title: "Deployment Failed",
    objectName: "payment-svc",
    age: "15m ago",
    provider: "AWS",
    region: "APAC",
    environment: "PRD",
    href: catalogHref("/deployments", {
      provider: "AWS",
      region: "APAC",
      environment: "PRD",
      selected: "dep-ap-southeast-1-prd-k8s",
    }),
  },
];

export const FLEET_AUDIT: FleetAuditEvent[] = [
  {
    id: "aud-emea-uat-view",
    event: "Environment viewed",
    actor: "ops@cloudops.local",
    objectName: "eu-west-1-uat-k8s",
    detail: "Audit event recorded without secret values",
    age: "1h ago",
    ...pick("AWS", "EMEA", "UAT"),
  },
  {
    id: "aud-amer-prd-cert",
    event: "Certificate catalog opened",
    actor: "ops@cloudops.local",
    objectName: "ingress-tls-wildcard",
    detail: "Expiration metadata only; private keys not retrieved",
    age: "1h ago",
    ...pick("AWS", "AMER", "PRD"),
  },
  {
    id: "aud-emea-npd-pipe",
    event: "Pipeline failure recorded",
    actor: "pipeline-bot",
    objectName: "data-sync",
    detail: "Result stored without secret values",
    age: "2h ago",
    ...pick("AWS", "EMEA", "NPD"),
  },
  {
    id: "aud-amer-int-github",
    event: "GitHub workflow recorded",
    actor: "github-sync",
    objectName: "auth-build",
    detail: "Workflow metadata only; tokens never stored",
    age: "1h ago",
    ...pick("AWS", "AMER", "INT/TST"),
  },
  {
    id: "aud-apac-prd-deploy",
    event: "Deployment failure recorded",
    actor: "deploy-controller",
    objectName: "payment-svc",
    detail: "Rollout aborted; no secret values included",
    age: "15m ago",
    ...pick("AWS", "APAC", "PRD"),
  },
  {
    id: "aud-china-uat-alert",
    event: "Alert acknowledged",
    actor: "sre-amer@cloudops.local",
    objectName: "prometheus-server",
    detail: "High memory warning retained without credentials",
    age: "2h ago",
    ...pick("Alibaba", "China", "UAT"),
  },
  {
    id: "aud-china-prd-export",
    event: "Audit log exported",
    actor: "auditor@cloudops.local",
    objectName: "prod-china",
    detail: "Export destination recorded; no secret values included",
    age: "6h ago",
    ...pick("Alibaba", "China", "PRD"),
  },
  {
    id: "aud-amer-dev-view",
    event: "Environment viewed",
    actor: "ops@cloudops.local",
    objectName: "us-east-1-dev-k8s",
    detail: "Non-production view recorded without secret values",
    age: "3h ago",
    ...pick("AWS", "AMER", "DEV"),
  },
];

export const ADMIN_USERS: AdminUser[] = [
  {
    id: "user-ops",
    user: "ops@cloudops.local",
    role: "Platform Admin",
    scope: "All providers",
    lastActive: "2m ago",
  },
  {
    id: "user-sre",
    user: "sre-amer@cloudops.local",
    role: "SRE",
    scope: "AWS AMER",
    lastActive: "18m ago",
  },
  {
    id: "user-auditor",
    user: "auditor@cloudops.local",
    role: "Read-only",
    scope: "Audit · Production",
    lastActive: "6h ago",
  },
];

export const ADMIN_INTEGRATIONS: AdminIntegration[] = [
  {
    id: "int-aws",
    name: "AWS Organizations",
    status: "Connected",
    scope: "AMER · EMEA · APAC",
    note: "Account inventory only; credentials stay in vault",
  },
  {
    id: "int-alibaba",
    name: "Alibaba Cloud",
    status: "Connected",
    scope: "China",
    note: "ACK inventory only; credentials stay in vault",
  },
  {
    id: "int-github",
    name: "GitHub App cloudops-platform",
    status: "Connected",
    scope: "Actions · Variables",
    note: "Connection state only; tokens are never displayed",
  },
];

function pick(provider: Provider, region: Region, environment: Environment) {
  return { provider, region, environment };
}

function scope(provider: Provider, region: Region, environment: Environment) {
  const identity = getEnvironmentIdentity(provider, region, environment);
  return {
    provider,
    region,
    environment,
    cluster: identity.clusterName,
  };
}

export function filterByScope<T extends { provider: Provider; region: Region; environment: Environment }>(
  rows: T[],
  filters: ScopeFilters,
): T[] {
  return rows.filter((row) => matchesCatalogFilters(row, filters));
}

export function filterInfrastructure(filters: ScopeFilters): InfrastructureAccount[] {
  return INFRASTRUCTURE_ACCOUNTS.filter((item) => {
    if (filters.provider !== "all" && item.provider !== filters.provider) return false;
    if (filters.region !== "all" && item.region !== filters.region) return false;
    if (filters.environment !== "all" && !item.hostedEnvironments.includes(filters.environment)) {
      return false;
    }
    return true;
  });
}

export function summarizeStatus(
  rows: { status?: string; result?: string; issue?: string; severity?: string; accountClass?: string }[],
  kind: "clusters" | "apps" | "health" | "runs" | "alerts" | "accounts",
) {
  if (kind === "clusters") {
    return {
      inScope: rows.length,
      healthy: rows.filter((row) => row.status === "Healthy").length,
      degraded: rows.filter((row) => row.status === "Degraded").length,
      unreachable: rows.filter((row) => row.status === "Unreachable").length,
    };
  }
  if (kind === "apps") {
    return {
      inScope: rows.length,
      healthy: rows.filter((row) => row.issue === "Healthy").length,
      degraded: rows.filter((row) => row.issue !== "Healthy").length,
    };
  }
  if (kind === "health") {
    return {
      inScope: rows.length,
      passing: rows.filter((row) => row.status === "Passing").length,
      warning: rows.filter((row) => row.status === "Warning").length,
      failing: rows.filter((row) => row.status === "Failing").length,
    };
  }
  if (kind === "runs") {
    return {
      inScope: rows.length,
      succeeded: rows.filter((row) => row.result === "Succeeded").length,
      failed: rows.filter((row) => row.result === "Failed").length,
      running: rows.filter((row) => row.result === "Running").length,
    };
  }
  if (kind === "alerts") {
    return {
      inScope: rows.length,
      critical: rows.filter((row) => row.severity === "critical").length,
      warning: rows.filter((row) => row.severity === "warning").length,
      info: rows.filter((row) => row.severity === "info").length,
    };
  }
  return {
    inScope: rows.length,
    production: rows.filter((row) => row.accountClass === "Production").length,
    nonProduction: rows.filter((row) => row.accountClass === "Non-production").length,
  };
}

export function countProduction<T extends { environment: Environment }>(rows: T[]): number {
  return rows.filter((row) => isProductionEnvironment(row.environment)).length;
}

export function countPrd<T extends { environment: Environment }>(rows: T[]): number {
  return rows.filter((row) => row.environment === "PRD").length;
}

export function fleetHref(
  path: string,
  item: { provider: Provider; region: Region; environment: Environment; id?: string },
): string {
  return catalogHref(path, {
    provider: item.provider,
    region: item.region,
    environment: item.environment,
    selected: item.id,
  });
}

function allStrings(): string[] {
  return [
    ...INFRASTRUCTURE_ACCOUNTS.flatMap((item) => [
      item.account,
      item.accountClass,
      item.cloudRegion,
      item.environments,
    ]),
    ...FLEET_CLUSTERS.flatMap((item) => [item.name, item.account, item.appsLabel, item.status]),
    ...FLEET_APPLICATIONS.flatMap((item) => [item.name, item.namespace, item.replicas, item.issue, item.cluster]),
    ...FLEET_HEALTH_CHECKS.flatMap((item) => [item.name, item.target, item.checkType, item.status, item.cluster]),
    ...FLEET_DEPLOYMENTS.flatMap((item) => [item.name, item.detail, item.result]),
    ...FLEET_PIPELINES.flatMap((item) => [item.name, item.detail, item.result]),
    ...FLEET_GITHUB_RUNS.flatMap((item) => [item.name, item.detail, item.result]),
    ...FLEET_JOBS.flatMap((item) => [item.name, item.detail, item.result]),
    ...FLEET_ALERTS.flatMap((item) => [item.title, item.objectName]),
    ...FLEET_AUDIT.flatMap((item) => [item.event, item.actor, item.objectName, item.detail]),
    ...ADMIN_USERS.flatMap((item) => [item.user, item.role, item.scope]),
    ...ADMIN_INTEGRATIONS.flatMap((item) => [item.name, item.status, item.scope, item.note]),
  ];
}

assertNoSecretValues(allStrings());
