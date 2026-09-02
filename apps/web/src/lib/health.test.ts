import { describe, expect, it } from "vitest";
import { healthHref, healthTone, parseHealthFilters } from "./health";

describe("health console helpers", () => {
  it("builds application and incident hrefs without calculating health", () => {
    expect(healthHref({ app: "payments-api", tab: "timeline" })).toBe("/health-checks?app=payments-api&tab=timeline");
    expect(parseHealthFilters({ app: "payments-api", incident: "inc-1" }).incident).toBe("inc-1");
  });

  it("maps backend status strings for display only", () => {
    expect(healthTone("HEALTHY")).toBe("healthy");
    expect(healthTone("DEGRADED")).toBe("warning");
    expect(healthTone("UNHEALTHY")).toBe("critical");
    expect(healthTone("CRITICAL")).toBe("critical");
    expect(healthTone("UNKNOWN")).toBe("muted");
  });
});
