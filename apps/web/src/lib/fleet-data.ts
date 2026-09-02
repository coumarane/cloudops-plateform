import { isProductionEnvironment } from "./dashboard";
import { matchesCatalogFilters } from "./catalog";
import type { AccountRecord, ApplicationRecord, ClusterRecord, HealthCheckRecord, RunRecord } from "./domain";
import type { Environment, Provider, Region } from "./types";

export type ScopeFilters = {
  provider: Provider | "all";
  region: Region | "all";
  environment: Environment | "all";
};

export type InfrastructureAccount = AccountRecord;
export type FleetCluster = ClusterRecord;
export type FleetApplication = ApplicationRecord;
export type FleetHealthCheck = HealthCheckRecord;
export type FleetRun = RunRecord;

export function filterByScope<T extends { provider: Provider; region: Region; environment: Environment }>(
  rows: T[],
  filters: ScopeFilters,
): T[] {
  return rows.filter((row) => matchesCatalogFilters(row, filters));
}

export function filterInfrastructure(rows: AccountRecord[], filters: ScopeFilters): AccountRecord[] {
  return rows.filter((item) => {
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
