import { describe, expect, it } from "vitest";
import {
  ENVIRONMENT_TABS,
  environmentHref,
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  parseTab,
} from "./environment";
import { listEnvironmentIdentities } from "./environment-data";

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
    expect(parseTab("alerts")).toBe("alerts");
    expect(parseTab("configuration")).toBe("configuration");
    expect(parseTab("unknown")).toBe("overview");
    expect(ENVIRONMENT_TABS).toEqual([
      "overview",
      "clusters",
      "applications",
      "certificates",
      "pipelines",
      "health",
      "alerts",
      "configuration",
      "secrets",
      "deployments",
      "github",
      "audit",
    ]);
  });

  it("rejects invalid provider and region combinations", () => {
    expect(parseProvider("gcp")).toBeNull();
    expect(parseRegion("latam")).toBeNull();
  });

  it("lists topology for AWS AMER/EMEA/APAC and Alibaba China", () => {
    const scopes = new Set(listEnvironmentIdentities().map((item) => `${item.provider} ${item.region}`));
    expect(scopes).toEqual(new Set(["AWS AMER", "AWS EMEA", "AWS APAC", "Alibaba China"]));
    expect(listEnvironmentIdentities().find((item) => item.provider === "AWS" && item.region === "EMEA" && item.environment === "UAT")?.account).toBe(
      "aws-emea-nonprod",
    );
    expect(
      listEnvironmentIdentities().find(
        (item) => item.provider === "Alibaba" && item.region === "China" && item.environment === "DEV",
      )?.account,
    ).toBe("alibaba-china-nonprod");
    expect(
      listEnvironmentIdentities().find(
        (item) => item.provider === "Alibaba" && item.region === "China" && item.environment === "PRD",
      )?.account,
    ).toBe("alibaba-china-prod");
  });
});
