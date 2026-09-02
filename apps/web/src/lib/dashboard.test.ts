import { describe, expect, it } from "vitest";
import { containsSecretValue, filterAlerts, filterRows, summarizeKpis } from "./dashboard";
import { MATRIX_ROWS, OPERATIONAL_ALERTS } from "./mock-data";

describe("dashboard aggregations", () => {
  it("unfiltered KPIs distinguish production incidents without leaking secret values", () => {
    const summary = summarizeKpis(MATRIX_ROWS, {
      provider: "all",
      region: "all",
      environment: "all",
    });

    expect(summary.clustersUnreachable).toBe(1);
    expect(summary.clustersDegraded).toBe(2);
    expect(summary.githubFailures).toBe(1);
    expect(summary.failedDeploys).toBe(1);
    expect(summary.pipelineFailures).toBe(1);
    expect(summary.certsExpiring14d).toBe(1);
    expect(summary.secretsOverdue).toBe(1);
    expect(summary.openAlerts).toBe(4);
    expect(containsSecretValue("ingress-tls-wildcard (12 days)")).toBe(false);
    expect(containsSecretValue("password=hunter2")).toBe(true);
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
    const alerts = filterAlerts(OPERATIONAL_ALERTS, {
      provider: "all",
      region: "all",
      environment: "PRD",
    });
    expect(alerts).toHaveLength(1);
    expect(alerts[0]?.environment).toBe("PRD");
    expect(alerts[0]?.region).toBe("AMER");
  });
});
