import { describe, expect, it } from "vitest";
import { containsSecretValue } from "./dashboard";
import {
  ENVIRONMENT_TABS,
  environmentHref,
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  parseTab,
} from "./environment";
import {
  environmentRecordStrings,
  getEnvironmentRecord,
  listEnvironmentIdentities,
} from "./environment-data";

describe("environment routing", () => {
  it("uses int-tst for INT/TST and keeps production slugs literal", () => {
    expect(environmentToSlug("INT/TST")).toBe("int-tst");
    expect(parseEnvironment("int-tst")).toBe("INT/TST");
    expect(environmentToSlug("PRD")).toBe("prd");
    expect(parseEnvironment("prd")).toBe("PRD");
  });

  it("builds tabbed environment URLs without exposing secret values", () => {
    expect(environmentHref("AWS", "EMEA", "UAT")).toBe("/environments/aws/emea/uat");
    expect(environmentHref("AWS", "AMER", "INT/TST", "github")).toBe(
      "/environments/aws/amer/int-tst?tab=github",
    );
    expect(parseTab("secrets")).toBe("secrets");
    expect(parseTab("unknown")).toBe("overview");
    expect(ENVIRONMENT_TABS).toEqual([
      "overview",
      "clusters",
      "applications",
      "secrets",
      "certificates",
      "deployments",
      "pipelines",
      "github",
      "health",
      "audit",
    ]);
  });

  it("rejects invalid provider and region combinations", () => {
    expect(parseProvider("gcp")).toBeNull();
    expect(parseRegion("latam")).toBeNull();
  });
});

describe("environment records", () => {
  it("never includes secret values in environment details data", () => {
    for (const identity of listEnvironmentIdentities()) {
      const record = getEnvironmentRecord(identity.provider, identity.region, identity.environment);
      for (const value of environmentRecordStrings(record)) {
        expect(containsSecretValue(value)).toBe(false);
      }
      expect(record.secrets.every((secret) => !("value" in secret))).toBe(true);
    }
  });

  it("models AWS EMEA UAT from the Stitch screen", () => {
    const record = getEnvironmentRecord("AWS", "EMEA", "UAT");
    expect(record.identity.account).toBe("nonprod-emea");
    expect(record.clusters[0]?.status).toBe("Unreachable");
    expect(record.applications).toHaveLength(4);
    expect(record.secrets[0]?.name).toBe("db-credentials-finance");
    expect(record.secrets[0]?.status).toBe("Overdue");
  });

  it("marks production accounts for PRD environments", () => {
    const record = getEnvironmentRecord("AWS", "AMER", "PRD");
    expect(record.identity.account).toBe("prod-amer");
    expect(record.certificates[0]?.name).toBe("ingress-tls-wildcard");
  });
});
