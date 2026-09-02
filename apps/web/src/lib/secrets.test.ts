import { describe, expect, it } from "vitest";
import { containsSecretValue } from "./dashboard";
import { filterManagedSecrets, managedSecretStrings, MANAGED_SECRETS, summarizeSecrets } from "./secrets-data";
import { parseSecretAction, secretsHref } from "./secrets";

describe("secrets management", () => {
  it("never includes secret values in catalog or history", () => {
    for (const secret of MANAGED_SECRETS) {
      expect("value" in secret).toBe(false);
      for (const value of managedSecretStrings(secret)) {
        expect(containsSecretValue(value)).toBe(false);
      }
    }
  });

  it("filters by provider, region, account, and environment hierarchy", () => {
    const prdAmer = filterManagedSecrets(MANAGED_SECRETS, {
      provider: "AWS",
      region: "AMER",
      account: "prod-amer",
      environment: "PRD",
    });
    expect(prdAmer.every((secret) => secret.environment === "PRD")).toBe(true);
    expect(prdAmer.every((secret) => secret.account === "prod-amer")).toBe(true);
    expect(prdAmer.map((secret) => secret.name)).toContain("app-runtime-credentials");
  });

  it("builds hierarchy URLs without embedding secret values", () => {
    expect(
      secretsHref({
        provider: "AWS",
        region: "AMER",
        account: "prod-amer",
        environment: "PRD",
        secret: "sec-amer-prd-app",
        action: "rotate",
      }),
    ).toBe(
      "/secrets?provider=aws&region=amer&account=prod-amer&environment=prd&secret=sec-amer-prd-app&action=rotate",
    );
    expect(parseSecretAction("rotate")).toBe("rotate");
    expect(parseSecretAction("reveal")).toBeNull();
  });

  it("summarizes overdue and PRD rows for the production warning", () => {
    const summary = summarizeSecrets(MANAGED_SECRETS);
    expect(summary.overdue).toBeGreaterThan(0);
    expect(summary.prd).toBeGreaterThan(0);
    expect(MANAGED_SECRETS.some((secret) => secret.environment === "PRD")).toBe(true);
  });
});
