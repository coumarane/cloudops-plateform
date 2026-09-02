import { catalogHref } from "./catalog";
import { certificatesHref } from "./certificates";
import { assertNoSecretValues, emptyMetrics } from "./dashboard";
import { ENVIRONMENTS, type CellMetrics, type MatrixRow, type OperationalAlert, type RecentFailure } from "./types";

function cell(overrides: Partial<CellMetrics> = {}): CellMetrics {
  return {
    ...emptyMetrics(),
    clustersHealthy: 1,
    appsHealthy: 9,
    ...overrides,
  };
}

function row(
  provider: MatrixRow["provider"],
  platform: MatrixRow["platform"],
  region: MatrixRow["region"],
  cells: Partial<Record<(typeof ENVIRONMENTS)[number], Partial<CellMetrics>>>,
): MatrixRow {
  const filled = Object.fromEntries(
    ENVIRONMENTS.map((environment) => [environment, cell(cells[environment])]),
  ) as MatrixRow["cells"];

  if (environmentHasDevExtra(region)) {
    filled.DEV = cell({
      ...cells.DEV,
      clustersHealthy: 2,
      appsHealthy: 12,
    });
  }

  return { provider, platform, region, cells: filled };
}

function environmentHasDevExtra(region: MatrixRow["region"]): boolean {
  return region === "AMER" || region === "EMEA" || region === "APAC" || region === "China";
}

export const LAST_SYNCED_LABEL = "14:32:45 UTC";

export const MATRIX_ROWS: MatrixRow[] = [
  row("AWS", "EKS", "AMER", {
    "INT/TST": { githubFailures: 1, appsHealthy: 8 },
    UAT: { clustersHealthy: 0, clustersDegraded: 1, secretsOverdue: 1, appsHealthy: 8 },
    PRD: { certsExpiring14d: 1, nextCertExpiryDays: 12, appsHealthy: 11, openAlerts: 1 },
  }),
  row("AWS", "EKS", "EMEA", {
    UAT: {
      clustersHealthy: 0,
      clustersUnreachable: 1,
      appsHealthy: 0,
      appsDegraded: 4,
      openAlerts: 1,
    },
    NPD: { pipelineFailures: 1, appsHealthy: 8 },
  }),
  row("AWS", "EKS", "APAC", {
    "INT/TST": { clustersHealthy: 0, clustersDegraded: 1, appsHealthy: 7, appsDegraded: 1 },
    PRD: { failedDeploys: 1, appsHealthy: 10 },
  }),
  row("Alibaba", "ACK", "China", {
    UAT: { openAlerts: 2, appsHealthy: 8 },
    PRD: { secretsDueSoon: 1, nextSecretDueDays: 4, appsHealthy: 11 },
  }),
];

export const OPERATIONAL_ALERTS: OperationalAlert[] = [
  {
    id: "alert-emea-uat-cluster",
    severity: "critical",
    title: "Cluster Unreachable",
    objectName: "eu-west-1-uat-k8s",
    provider: "AWS",
    region: "EMEA",
    environment: "UAT",
    age: "10m ago",
    href: catalogHref("/clusters", {
      provider: "AWS",
      region: "EMEA",
      environment: "UAT",
      selected: "eu-west-1-uat-k8s",
    }),
  },
  {
    id: "alert-amer-prd-cert",
    severity: "warning",
    title: "Cert Expiring",
    objectName: "ingress-tls-wildcard (12 days)",
    provider: "AWS",
    region: "AMER",
    environment: "PRD",
    age: "1h ago",
    href: certificatesHref({
      provider: "AWS",
      region: "AMER",
      environment: "PRD",
      certificate: "cert-amer-prd-wildcard",
    }),
  },
  {
    id: "alert-china-uat-memory",
    severity: "info",
    title: "High Memory Usage",
    objectName: "prometheus-server (88%)",
    provider: "Alibaba",
    region: "China",
    environment: "UAT",
    age: "2h ago",
    href: catalogHref("/health-checks", {
      provider: "Alibaba",
      region: "China",
      environment: "UAT",
      selected: "hc-china-uat-prometheus",
    }),
  },
  {
    id: "alert-china-uat-restarts",
    severity: "info",
    title: "Pod Restart Loop",
    objectName: "api-gateway-v2",
    provider: "Alibaba",
    region: "China",
    environment: "UAT",
    age: "3h ago",
    href: catalogHref("/applications", {
      provider: "Alibaba",
      region: "China",
      environment: "UAT",
      selected: "app-china-uat-gateway",
    }),
  },
];

export const RECENT_FAILURES: RecentFailure[] = [
  {
    id: "fail-apac-prd-deploy",
    kind: "deployment",
    name: "payment-svc",
    provider: "AWS",
    region: "APAC",
    environment: "PRD",
    age: "15m ago",
    href: catalogHref("/deployments", {
      provider: "AWS",
      region: "APAC",
      environment: "PRD",
      selected: "dep-ap-southeast-1-prd-k8s",
    }),
  },
  {
    id: "fail-amer-int-github",
    kind: "github",
    name: "auth-build",
    provider: "AWS",
    region: "AMER",
    environment: "INT/TST",
    age: "1h ago",
    href: catalogHref("/github", {
      provider: "AWS",
      region: "AMER",
      environment: "INT/TST",
      selected: "gh-us-east-1-int-k8s",
    }),
  },
  {
    id: "fail-emea-npd-pipeline",
    kind: "pipeline",
    name: "data-sync",
    provider: "AWS",
    region: "EMEA",
    environment: "NPD",
    age: "2h ago",
    href: catalogHref("/pipelines", {
      provider: "AWS",
      region: "EMEA",
      environment: "NPD",
      selected: "pipe-eu-west-1-npd-k8s",
    }),
  },
];

assertNoSecretValues([
  ...OPERATIONAL_ALERTS.flatMap((alert) => [alert.title, alert.objectName]),
  ...RECENT_FAILURES.map((failure) => failure.name),
]);
