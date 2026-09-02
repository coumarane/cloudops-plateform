import {
  ENVIRONMENTS,
  PRODUCTION_ENVIRONMENTS,
  type CellMetrics,
  type DashboardFilters,
  type Environment,
  type KpiSummary,
  type MatrixRow,
  type OperationalAlert,
  type RecentFailure,
  type Region,
  type Severity,
} from "./types";

const HEALTHY_CELL: CellMetrics = {
  clustersHealthy: 1,
  clustersDegraded: 0,
  clustersUnreachable: 0,
  appsHealthy: 9,
  appsDegraded: 0,
  certsExpiring14d: 0,
  secretsOverdue: 0,
  secretsDueSoon: 0,
  failedDeploys: 0,
  githubFailures: 0,
  pipelineFailures: 0,
  openAlerts: 0,
};

export function emptyMetrics(): CellMetrics {
  return { ...HEALTHY_CELL, clustersHealthy: 0, appsHealthy: 0 };
}

export function isProductionEnvironment(environment: Environment): boolean {
  return (PRODUCTION_ENVIRONMENTS as readonly string[]).includes(environment);
}

export function regionsForProvider(provider: DashboardFilters["provider"]): Region[] {
  if (provider === "AWS") {
    return ["AMER", "EMEA", "APAC"];
  }
  if (provider === "Alibaba") {
    return ["China"];
  }
  return ["AMER", "EMEA", "APAC", "China"];
}

export function cellSeverity(cell: CellMetrics): Severity {
  if (
    cell.clustersUnreachable > 0 ||
    cell.failedDeploys > 0 ||
    cell.githubFailures > 0 ||
    cell.pipelineFailures > 0 ||
    (cell.appsUnhealthy ?? 0) > 0 ||
    (cell.appsCritical ?? 0) > 0
  ) {
    return "critical";
  }
  if (
    cell.clustersDegraded > 0 ||
    cell.appsDegraded > 0 ||
    cell.certsExpiring14d > 0 ||
    cell.secretsOverdue > 0 ||
    cell.secretsDueSoon > 0 ||
    cell.openAlerts > 0 ||
    (cell.openIncidents ?? 0) > 0
  ) {
    return "warning";
  }
  return "healthy";
}

export function cellExceptionLabel(cell: CellMetrics): string | undefined {
  if (cell.clustersUnreachable > 0) {
    return "Cluster Down";
  }
  if ((cell.appsCritical ?? 0) > 0) {
    return `${cell.appsCritical} App Crit.`;
  }
  if ((cell.appsUnhealthy ?? 0) > 0) {
    return `${cell.appsUnhealthy} App Unh.`;
  }
  if ((cell.openIncidents ?? 0) > 0) {
    return `${cell.openIncidents} Incident`;
  }
  if (cell.githubFailures > 0) {
    return `${cell.githubFailures} GitHub`;
  }
  if (cell.pipelineFailures > 0) {
    return `${cell.pipelineFailures} Pipeline`;
  }
  if (cell.failedDeploys > 0) {
    return `${cell.failedDeploys} Deploy`;
  }
  if (cell.certsExpiring14d > 0) {
    return cell.nextCertExpiryDays != null
      ? `${cell.certsExpiring14d} Cert (${cell.nextCertExpiryDays}d)`
      : `${cell.certsExpiring14d} Cert`;
  }
  if (cell.secretsOverdue > 0) {
    return `${cell.secretsOverdue} Secret Due`;
  }
  if (cell.secretsDueSoon > 0) {
    return cell.nextSecretDueDays != null
      ? `${cell.secretsDueSoon} Secret (${cell.nextSecretDueDays}d)`
      : `${cell.secretsDueSoon} Secret`;
  }
  if (cell.appsDegraded > 0) {
    return `${cell.appsDegraded} App Deg.`;
  }
  if (cell.openAlerts > 0) {
    return `${cell.openAlerts} Alerts`;
  }
  return undefined;
}

export function filterRows(rows: MatrixRow[], filters: DashboardFilters): MatrixRow[] {
  return rows.filter((row) => {
    if (filters.provider !== "all" && row.provider !== filters.provider) {
      return false;
    }
    if (filters.region !== "all" && row.region !== filters.region) {
      return false;
    }
    return true;
  });
}

export function filterAlerts(
  alerts: OperationalAlert[],
  filters: DashboardFilters,
): OperationalAlert[] {
  return alerts.filter((alert) => matchesFilters(alert, filters));
}

export function filterFailures(
  failures: RecentFailure[],
  filters: DashboardFilters,
): RecentFailure[] {
  return failures.filter((failure) => matchesFilters(failure, filters));
}

function matchesFilters(
  item: { provider: MatrixRow["provider"]; region: Region; environment: Environment },
  filters: DashboardFilters,
): boolean {
  if (filters.provider !== "all" && item.provider !== filters.provider) {
    return false;
  }
  if (filters.region !== "all" && item.region !== filters.region) {
    return false;
  }
  if (filters.environment !== "all" && item.environment !== filters.environment) {
    return false;
  }
  return true;
}

export function summarizeKpis(rows: MatrixRow[], filters: DashboardFilters): KpiSummary {
  const summary: KpiSummary = {
    clustersHealthy: 0,
    clustersDegraded: 0,
    clustersUnreachable: 0,
    appsHealthy: 0,
    appsDegraded: 0,
    appsUnhealthy: 0,
    appsCritical: 0,
    certsExpiring14d: 0,
    certsHealthy: 0,
    certsExpiring60d: 0,
    certsExpiring30d: 0,
    certsExpiring7d: 0,
    certsExpired: 0,
    secretsOverdue: 0,
    failedDeploys: 0,
    githubFailures: 0,
    githubWorkflowsRunning: 0,
    githubWorkflowsFailed: 0,
    githubWorkflowsSucceeded: 0,
    pipelineFailures: 0,
    pipelineRunsToday: 0,
    pipelinesRunning: 0,
    pipelinesFailed: 0,
    pipelinesFailedPrd: 0,
    pipelineAverageDurationSeconds: 0,
    openAlerts: 0,
    openIncidents: 0,
    unhealthyClusters: 0,
  };

  const environments =
    filters.environment === "all" ? ENVIRONMENTS : ([filters.environment] as const);

  for (const row of filterRows(rows, filters)) {
    for (const environment of environments) {
      const cell = row.cells[environment];
      summary.clustersHealthy += cell.clustersHealthy;
      summary.clustersDegraded += cell.clustersDegraded;
      summary.clustersUnreachable += cell.clustersUnreachable;
      summary.appsHealthy += cell.appsHealthy;
      summary.appsDegraded += cell.appsDegraded;
      summary.appsUnhealthy = (summary.appsUnhealthy ?? 0) + (cell.appsUnhealthy ?? 0);
      summary.appsCritical = (summary.appsCritical ?? 0) + (cell.appsCritical ?? 0);
      summary.certsExpiring14d += cell.certsExpiring14d;
      summary.certsHealthy = (summary.certsHealthy ?? 0) + (cell.certsHealthy ?? 0);
      summary.certsExpiring60d = (summary.certsExpiring60d ?? 0) + (cell.certsExpiring60d ?? 0);
      summary.certsExpiring30d = (summary.certsExpiring30d ?? 0) + (cell.certsExpiring30d ?? 0);
      summary.certsExpiring7d = (summary.certsExpiring7d ?? 0) + (cell.certsExpiring7d ?? 0);
      summary.certsExpired = (summary.certsExpired ?? 0) + (cell.certsExpired ?? 0);
      summary.secretsOverdue += cell.secretsOverdue;
      summary.failedDeploys += cell.failedDeploys;
      summary.githubFailures += cell.githubFailures;
      summary.pipelineFailures += cell.pipelineFailures;
      summary.openAlerts += cell.openAlerts;
      summary.openIncidents = (summary.openIncidents ?? 0) + (cell.openIncidents ?? 0);
    }
  }

  return summary;
}

const SECRET_VALUE_PATTERN =
  /(password|token|apikey|api_key|secret[_-]?value|private[_-]?key)\s*[:=]/i;

export function containsSecretValue(value: string): boolean {
  return SECRET_VALUE_PATTERN.test(value);
}

export function assertNoSecretValues(values: string[]): void {
  const leaked = values.filter(containsSecretValue);
  if (leaked.length > 0) {
    throw new Error("Secret values must never be rendered or stored in dashboard data.");
  }
}
