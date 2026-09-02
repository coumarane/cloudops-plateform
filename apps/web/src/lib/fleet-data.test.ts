import { describe, expect, it } from "vitest";
import { catalogHref, parseCatalogFilters } from "./catalog";
import { containsSecretValue } from "./dashboard";
import { PLACEHOLDER_SECTIONS } from "./navigation";
import {
  ADMIN_INTEGRATIONS,
  ADMIN_USERS,
  FLEET_ALERTS,
  FLEET_APPLICATIONS,
  FLEET_AUDIT,
  FLEET_CLUSTERS,
  FLEET_DEPLOYMENTS,
  FLEET_GITHUB_RUNS,
  FLEET_HEALTH_CHECKS,
  FLEET_JOBS,
  FLEET_PIPELINES,
  filterByScope,
  filterInfrastructure,
  INFRASTRUCTURE_ACCOUNTS,
} from "./fleet-data";
import { OPERATIONAL_ALERTS, RECENT_FAILURES } from "./mock-data";

function scopes<T extends { provider: string; region: string }>(rows: T[]) {
  return new Set(rows.map((row) => `${row.provider} ${row.region}`));
}

describe("remaining console catalogs", () => {
  it("implements every primary nav route", () => {
    expect(PLACEHOLDER_SECTIONS).toEqual([]);
  });

  it("covers AWS AMER, EMEA, APAC, and Alibaba China", () => {
    const expected = new Set(["AWS AMER", "AWS EMEA", "AWS APAC", "Alibaba China"]);
    expect(scopes(INFRASTRUCTURE_ACCOUNTS)).toEqual(expected);
    expect(scopes(FLEET_CLUSTERS)).toEqual(expected);
    expect(scopes(FLEET_APPLICATIONS)).toEqual(expected);
    expect(scopes(FLEET_HEALTH_CHECKS)).toEqual(expected);
    expect(scopes(FLEET_DEPLOYMENTS)).toEqual(expected);
    expect(scopes(FLEET_PIPELINES)).toEqual(expected);
    expect(scopes(FLEET_GITHUB_RUNS)).toEqual(expected);
    expect(scopes(FLEET_JOBS)).toEqual(expected);
    expect(scopes(FLEET_ALERTS)).toEqual(expected);
    expect(scopes(FLEET_AUDIT)).toEqual(expected);
  });

  it("keeps known operational exceptions", () => {
    expect(FLEET_CLUSTERS.some((row) => row.name === "eu-west-1-uat-k8s" && row.status === "Unreachable")).toBe(
      true,
    );
    expect(FLEET_APPLICATIONS.some((row) => row.name === "payment-gateway-svc")).toBe(true);
    expect(FLEET_APPLICATIONS.some((row) => row.name === "payment-svc" && row.environment === "PRD")).toBe(true);
    expect(FLEET_DEPLOYMENTS.some((row) => row.name === "payment-svc" && row.result === "Failed")).toBe(true);
    expect(FLEET_PIPELINES.some((row) => row.name === "data-sync" && row.result === "Failed")).toBe(true);
    expect(FLEET_GITHUB_RUNS.some((row) => row.name === "auth-build" && row.result === "Failed")).toBe(true);
    expect(FLEET_HEALTH_CHECKS.some((row) => row.name === "kube-apiserver" && row.status === "Failing")).toBe(
      true,
    );
  });

  it("filters infrastructure accounts by hosted environment", () => {
    const prdAmer = filterInfrastructure({
      provider: "AWS",
      region: "AMER",
      environment: "PRD",
    });
    expect(prdAmer).toHaveLength(1);
    expect(prdAmer[0]?.account).toBe("prod-amer");
    expect(prdAmer[0]?.accountClass).toBe("Production");
  });

  it("filters fleet rows by provider and region", () => {
    const china = filterByScope(FLEET_CLUSTERS, {
      provider: "Alibaba",
      region: "China",
      environment: "all",
    });
    expect(china.every((row) => row.provider === "Alibaba" && row.region === "China")).toBe(true);
    expect(china.length).toBeGreaterThan(0);
  });

  it("never includes secret values, tokens, or private keys", () => {
    const values = [
      ...INFRASTRUCTURE_ACCOUNTS.flatMap((item) => [item.account, item.environments]),
      ...FLEET_CLUSTERS.map((item) => item.name),
      ...FLEET_APPLICATIONS.flatMap((item) => [item.name, item.issue]),
      ...FLEET_GITHUB_RUNS.map((item) => item.detail),
      ...FLEET_AUDIT.flatMap((item) => [item.detail, item.actor]),
      ...ADMIN_USERS.map((item) => item.user),
      ...ADMIN_INTEGRATIONS.flatMap((item) => [item.name, item.note]),
    ];
    for (const value of values) {
      expect(containsSecretValue(value)).toBe(false);
    }
    expect(ADMIN_INTEGRATIONS.every((item) => !containsSecretValue(item.note))).toBe(true);
  });

  it("builds catalog URLs for dashboard deep-links", () => {
    expect(
      catalogHref("/clusters", {
        provider: "AWS",
        region: "EMEA",
        environment: "UAT",
        selected: "eu-west-1-uat-k8s",
      }),
    ).toBe("/clusters?provider=aws&region=emea&environment=uat&selected=eu-west-1-uat-k8s");
    expect(parseCatalogFilters({ provider: "alibaba", region: "china", environment: "prd" })).toEqual({
      provider: "Alibaba",
      region: "China",
      environment: "PRD",
      selected: null,
    });
  });

  it("points dashboard failures and alerts at fleet catalogs", () => {
    expect(RECENT_FAILURES.find((item) => item.kind === "deployment")?.href).toContain("/deployments");
    expect(RECENT_FAILURES.find((item) => item.kind === "github")?.href).toContain("/github");
    expect(RECENT_FAILURES.find((item) => item.kind === "pipeline")?.href).toContain("/pipelines");
    expect(OPERATIONAL_ALERTS.find((item) => item.id === "alert-emea-uat-cluster")?.href).toContain("/clusters");
    expect(FLEET_ALERTS.some((item) => item.region === "APAC")).toBe(true);
    expect(FLEET_ALERTS.length).toBeGreaterThanOrEqual(4);
  });
});
