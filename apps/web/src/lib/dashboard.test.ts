import { describe, expect, it } from "vitest";
import { containsSecretValue, filterAlerts, filterRows, summarizeKpis, cellIsUnconfigured } from "./dashboard";
import type { MatrixRow, OperationalAlert } from "./types";

const MATRIX_ROWS: MatrixRow[] = [
  {
    provider: "AWS",
    platform: "EKS",
    region: "AMER",
    cells: {
      DEV: empty(),
      "INT/TST": { ...empty(), githubFailures: 1 },
      UAT: empty(),
      NPD: empty(),
      PRD: { ...empty(), certsExpiring14d: 1 },
    },
  },
  {
    provider: "Alibaba",
    platform: "ACK",
    region: "China",
    cells: {
      DEV: empty(),
      "INT/TST": empty(),
      UAT: empty(),
      NPD: empty(),
      PRD: empty(),
    },
  },
];

function empty() {
  return {
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
}

const ALERTS: OperationalAlert[] = [
  {
    id: "alert-amer-prd-cert",
    severity: "warning",
    title: "Cert Expiring",
    objectName: "ingress-tls-wildcard (12 days)",
    provider: "AWS",
    region: "AMER",
    environment: "PRD",
    age: "1h ago",
    href: "/certificates?provider=aws&region=amer&environment=prd&certificate=cert-amer-prd-wildcard",
  },
  {
    id: "alert-emea-uat-cluster",
    severity: "critical",
    title: "Cluster Unreachable",
    objectName: "eu-west-1-uat-k8s",
    provider: "AWS",
    region: "EMEA",
    environment: "UAT",
    age: "10m ago",
    href: "/clusters?provider=aws&region=emea&environment=uat&selected=eu-west-1-uat-k8s",
  },
];

describe("dashboard aggregations", () => {
  it("never treats object names as secret values", () => {
    expect(containsSecretValue("ingress-tls-wildcard (12 days)")).toBe(false);
    expect(containsSecretValue("password=hunter2")).toBe(true);
    expect(summarizeKpis(MATRIX_ROWS, { provider: "all", region: "all", environment: "all" }).githubFailures).toBe(1);
  });

  it("Alibaba filter keeps China and drops AWS regions", () => {
    const rows = filterRows(MATRIX_ROWS, {
      provider: "Alibaba",
      region: "all",
      environment: "all",
    });
    expect(rows.map((row) => row.region)).toEqual(["China"]);
  });

  it("PRD environment filter keeps the AMER certificate alert only", () => {
    const alerts = filterAlerts(ALERTS, {
      provider: "all",
      region: "all",
      environment: "PRD",
    });
    expect(alerts).toHaveLength(1);
    expect(alerts[0]?.href).toContain("/certificates");
  });

  it("treats unconfigured matrix cells as empty instead of healthy", () => {
    expect(
      cellIsUnconfigured({
        clustersHealthy: 0,
        clustersDegraded: 0,
        clustersUnreachable: 0,
        appsHealthy: 0,
        appsDegraded: 0,
        certsExpiring14d: 0,
        secretsOverdue: 0,
        secretsDueSoon: 0,
        failedDeploys: 0,
        githubFailures: 0,
        pipelineFailures: 0,
        openAlerts: 0,
      }),
    ).toBe(true);
    expect(cellIsUnconfigured({ ...empty(), live: true, clustersHealthy: 0, appsHealthy: 0 })).toBe(false);
  });
});
