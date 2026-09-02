import { assertNoSecretValues, emptyMetrics, isProductionEnvironment } from "./dashboard";
import { environmentHref } from "./environment";
import { MATRIX_ROWS } from "./mock-data";
import type { CellMetrics, Environment, KpiSummary, Provider, Region } from "./types";

export type EnvironmentIdentity = {
  provider: Provider;
  region: Region;
  environment: Environment;
  platform: "EKS" | "ACK";
  cloudRegion: string;
  account: string;
  clusterName: string;
};

export type EnvironmentCluster = {
  name: string;
  platform: "EKS" | "ACK";
  version: string;
  nodes: number;
  status: "Healthy" | "Degraded" | "Unreachable";
  appsLabel: string;
};

export type EnvironmentApplication = {
  name: string;
  namespace: string;
  replicas: string;
  issue: string;
  action: string;
};

export type EnvironmentSecret = {
  name: string;
  namespace: string;
  status: "OK" | "Overdue" | "Due soon";
  detail: string;
};

export type EnvironmentCertificate = {
  name: string;
  daysToExpiry: number;
};

export type EnvironmentActivity = {
  title: string;
  detail: string;
  age: string;
};

export type EnvironmentAlert = {
  title: string;
  objectName: string;
  age: string;
  severity: "critical" | "warning" | "info";
};

export type EnvironmentRecord = {
  identity: EnvironmentIdentity;
  clusters: EnvironmentCluster[];
  applications: EnvironmentApplication[];
  secrets: EnvironmentSecret[];
  certificates: EnvironmentCertificate[];
  deployments: EnvironmentActivity[];
  pipelines: EnvironmentActivity[];
  github: EnvironmentActivity[];
  health: EnvironmentActivity[];
  audit: EnvironmentActivity[];
  alerts: EnvironmentAlert[];
  recentActivity: EnvironmentActivity[];
};

const CLOUD_REGIONS: Record<string, string> = {
  "AWS-AMER": "us-east-1",
  "AWS-EMEA": "eu-west-1",
  "AWS-APAC": "ap-southeast-1",
  "Alibaba-China": "cn-hangzhou",
};

function accountName(provider: Provider, region: Region, environment: Environment): string {
  const classLabel = isProductionEnvironment(environment) ? "prod" : "nonprod";
  const regionKey = region.toLowerCase();
  return provider === "Alibaba" ? `${classLabel}-china` : `${classLabel}-${regionKey}`;
}

function clusterName(provider: Provider, region: Region, environment: Environment): string {
  const cloud = CLOUD_REGIONS[`${provider}-${region}`];
  const env = environment === "INT/TST" ? "int" : environment.toLowerCase();
  const suffix = provider === "Alibaba" ? "ack" : "k8s";
  return `${cloud}-${env}-${suffix}`;
}

export function getEnvironmentIdentity(
  provider: Provider,
  region: Region,
  environment: Environment,
): EnvironmentIdentity {
  return {
    provider,
    region,
    environment,
    platform: provider === "Alibaba" ? "ACK" : "EKS",
    cloudRegion: CLOUD_REGIONS[`${provider}-${region}`] ?? "",
    account: accountName(provider, region, environment),
    clusterName: clusterName(provider, region, environment),
  };
}

const EMEA_UAT: EnvironmentRecord = {
  identity: getEnvironmentIdentity("AWS", "EMEA", "UAT"),
  clusters: [
    {
      name: "eu-west-1-uat-k8s",
      platform: "EKS",
      version: "1.29",
      nodes: 12,
      status: "Unreachable",
      appsLabel: "4 degraded",
    },
  ],
  applications: [
    {
      name: "payment-gateway-svc",
      namespace: "finance-uat",
      replicas: "2/4",
      issue: "CrashLoopBackOff",
      action: "Logs",
    },
    {
      name: "user-profile-api",
      namespace: "users-uat",
      replicas: "0/2",
      issue: "ImagePullBackOff",
      action: "Events",
    },
    {
      name: "inventory-sync-worker",
      namespace: "logistics-uat",
      replicas: "1/1 (Not Ready)",
      issue: "ReadinessProbe Failed",
      action: "Describe",
    },
    {
      name: "notification-dispatcher",
      namespace: "core-uat",
      replicas: "1/3",
      issue: "OOMKilled",
      action: "Metrics",
    },
  ],
  secrets: [
    {
      name: "db-credentials-finance",
      namespace: "finance-uat",
      status: "Overdue",
      detail: "Rotation overdue",
    },
  ],
  certificates: [],
  deployments: [
    {
      title: "checkout-api rollout paused",
      detail: "Waiting on cluster connectivity",
      age: "25m ago",
    },
  ],
  pipelines: [
    {
      title: "uat-promote pipeline skipped",
      detail: "Gate blocked: cluster unreachable",
      age: "40m ago",
    },
  ],
  github: [
    {
      title: "workflow uat-deploy skipped",
      detail: "Initiated by GitHub Actions",
      age: "25m ago",
    },
  ],
  health: [
    {
      title: "kube-apiserver probe failing",
      detail: "eu-west-1-uat-k8s",
      age: "10m ago",
    },
  ],
  audit: [
    {
      title: "Audit log exported",
      detail: "Destination recorded; no secret values included",
      age: "3h ago",
    },
  ],
  alerts: [
    {
      title: "Cluster Unreachable",
      objectName: "eu-west-1-uat-k8s",
      age: "10m ago",
      severity: "critical",
    },
  ],
  recentActivity: [
    {
      title: "Deploy user-profile-api:v2.1.0",
      detail: "Initiated by GitHub Actions",
      age: "25m ago",
    },
    {
      title: "Pipeline nightly-db-backup completed",
      detail: "Duration: 12m 4s",
      age: "4h ago",
    },
    {
      title: "Audit log exported",
      detail: "System event; no secret values included",
      age: "6h ago",
    },
  ],
};

function recordFromMatrix(
  provider: Provider,
  region: Region,
  environment: Environment,
): EnvironmentRecord {
  const identity = getEnvironmentIdentity(provider, region, environment);
  const row = MATRIX_ROWS.find((item) => item.provider === provider && item.region === region);
  const cell = row?.cells[environment];
  const unreachable = (cell?.clustersUnreachable ?? 0) > 0;
  const degraded = (cell?.clustersDegraded ?? 0) > 0;
  const status: EnvironmentCluster["status"] = unreachable
    ? "Unreachable"
    : degraded
      ? "Degraded"
      : "Healthy";

  return {
    identity,
    clusters: [
      {
        name: identity.clusterName,
        platform: identity.platform,
        version: "1.29",
        nodes: environment === "DEV" ? 6 : 12,
        status,
        appsLabel: `${cell?.appsDegraded ?? 0} degraded / ${cell?.appsHealthy ?? 0} healthy`,
      },
    ],
    applications:
      (cell?.appsDegraded ?? 0) > 0
        ? [
            {
              name: "platform-api",
              namespace: `${environmentToNamespace(environment)}`,
              replicas: "2/3",
              issue: "Degraded",
              action: "Logs",
            },
          ]
        : [
            {
              name: "platform-api",
              namespace: `${environmentToNamespace(environment)}`,
              replicas: "3/3",
              issue: "Healthy",
              action: "Status",
            },
          ],
    secrets:
      (cell?.secretsOverdue ?? 0) > 0
        ? [
            {
              name: "app-runtime-credentials",
              namespace: environmentToNamespace(environment),
              status: "Overdue",
              detail: "Rotation overdue",
            },
          ]
        : (cell?.secretsDueSoon ?? 0) > 0
          ? [
              {
                name: "app-runtime-credentials",
                namespace: environmentToNamespace(environment),
                status: "Due soon",
                detail: `Due in ${cell?.nextSecretDueDays ?? 4}d`,
              },
            ]
          : [
              {
                name: "app-runtime-credentials",
                namespace: environmentToNamespace(environment),
                status: "OK",
                detail: "Rotation current",
              },
            ],
    certificates:
      (cell?.certsExpiring14d ?? 0) > 0
        ? [
            {
              name: "ingress-tls-wildcard",
              daysToExpiry: cell?.nextCertExpiryDays ?? 12,
            },
          ]
        : [],
    deployments:
      (cell?.failedDeploys ?? 0) > 0
        ? [{ title: "payment-svc deploy failed", detail: "Rollout aborted", age: "15m ago" }]
        : [{ title: "platform-api deploy succeeded", detail: "Rollout complete", age: "2h ago" }],
    pipelines:
      (cell?.pipelineFailures ?? 0) > 0
        ? [{ title: "data-sync pipeline failed", detail: "Stage test-gate", age: "2h ago" }]
        : [{ title: "env-sync pipeline succeeded", detail: "Last green run", age: "6h ago" }],
    github:
      (cell?.githubFailures ?? 0) > 0
        ? [{ title: "auth-build workflow failed", detail: "GitHub Actions", age: "1h ago" }]
        : [{ title: "ci-verify workflow succeeded", detail: "GitHub Actions", age: "4h ago" }],
    health: [
      {
        title: unreachable ? "API server unreachable" : "Probes passing",
        detail: identity.clusterName,
        age: "10m ago",
      },
    ],
    audit: [
      {
        title: "Environment viewed",
        detail: "Audit event recorded without secret values",
        age: "1h ago",
      },
    ],
    alerts:
      (cell?.openAlerts ?? 0) > 0 || unreachable
        ? [
            {
              title: unreachable ? "Cluster Unreachable" : "Environment warning",
              objectName: identity.clusterName,
              age: "10m ago",
              severity: unreachable ? "critical" : "warning",
            },
          ]
        : [],
    recentActivity: [
      ...(cell?.failedDeploys ?? 0) > 0
        ? [{ title: "payment-svc deploy failed", detail: "Rollout aborted", age: "15m ago" }]
        : [{ title: "platform-api deploy succeeded", detail: "Rollout complete", age: "2h ago" }],
      ...(cell?.pipelineFailures ?? 0) > 0
        ? [{ title: "data-sync pipeline failed", detail: "Stage test-gate", age: "2h ago" }]
        : [],
      {
        title: "Environment viewed",
        detail: "Audit event recorded without secret values",
        age: "1h ago",
      },
    ],
  };
}

function environmentToNamespace(environment: Environment): string {
  return environment === "INT/TST" ? "int-tst" : environment.toLowerCase();
}

export function getEnvironmentRecord(
  provider: Provider,
  region: Region,
  environment: Environment,
): EnvironmentRecord {
  if (provider === "AWS" && region === "EMEA" && environment === "UAT") {
    return EMEA_UAT;
  }
  return recordFromMatrix(provider, region, environment);
}

export function listEnvironmentIdentities(): EnvironmentIdentity[] {
  return MATRIX_ROWS.flatMap((row) =>
    (["DEV", "INT/TST", "UAT", "NPD", "PRD"] as Environment[]).map((environment) =>
      getEnvironmentIdentity(row.provider, row.region, environment),
    ),
  );
}

export function environmentDetailsHref(
  provider: Provider,
  region: Region,
  environment: Environment,
): string {
  return environmentHref(provider, region, environment);
}

export function environmentTitle(identity: EnvironmentIdentity): string {
  return `${identity.provider} ${identity.region} ${identity.environment}`;
}

export function getEnvironmentCell(
  provider: Provider,
  region: Region,
  environment: Environment,
): CellMetrics {
  const row = MATRIX_ROWS.find((item) => item.provider === provider && item.region === region);
  return row?.cells[environment] ?? emptyMetrics();
}

export function summarizeEnvironment(record: EnvironmentRecord): KpiSummary {
  const cell = getEnvironmentCell(
    record.identity.provider,
    record.identity.region,
    record.identity.environment,
  );
  const degradedApps = record.applications.filter((app) => app.issue !== "Healthy").length;
  const healthyApps = record.applications.filter((app) => app.issue === "Healthy").length;

  return {
    clustersHealthy: record.clusters.filter((cluster) => cluster.status === "Healthy").length,
    clustersDegraded: record.clusters.filter((cluster) => cluster.status === "Degraded").length,
    clustersUnreachable: record.clusters.filter((cluster) => cluster.status === "Unreachable").length,
    appsHealthy: healthyApps || cell.appsHealthy,
    appsDegraded: degradedApps || cell.appsDegraded,
    certsExpiring14d: record.certificates.length || cell.certsExpiring14d,
    secretsOverdue: record.secrets.filter((secret) => secret.status === "Overdue").length,
    failedDeploys: cell.failedDeploys,
    githubFailures: cell.githubFailures,
    pipelineFailures: cell.pipelineFailures,
    openAlerts: record.alerts.length || cell.openAlerts,
  };
}

export function environmentRecordStrings(record: EnvironmentRecord): string[] {
  return [
    record.identity.account,
    record.identity.clusterName,
    record.identity.cloudRegion,
    ...record.clusters.flatMap((cluster) => [cluster.name, cluster.appsLabel, cluster.status]),
    ...record.applications.flatMap((app) => [app.name, app.namespace, app.replicas, app.issue, app.action]),
    ...record.secrets.flatMap((secret) => [secret.name, secret.namespace, secret.status, secret.detail]),
    ...record.certificates.map((certificate) => certificate.name),
    ...record.deployments.flatMap((item) => [item.title, item.detail]),
    ...record.pipelines.flatMap((item) => [item.title, item.detail]),
    ...record.github.flatMap((item) => [item.title, item.detail]),
    ...record.health.flatMap((item) => [item.title, item.detail]),
    ...record.audit.flatMap((item) => [item.title, item.detail]),
    ...record.alerts.flatMap((alert) => [alert.title, alert.objectName]),
    ...record.recentActivity.flatMap((item) => [item.title, item.detail]),
  ];
}

function assertAllEnvironmentRecordsSafe(): void {
  for (const identity of listEnvironmentIdentities()) {
    assertNoSecretValues(
      environmentRecordStrings(
        getEnvironmentRecord(identity.provider, identity.region, identity.environment),
      ),
    );
  }
}

assertAllEnvironmentRecordsSafe();
