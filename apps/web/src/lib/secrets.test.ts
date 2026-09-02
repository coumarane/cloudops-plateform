import { describe, expect, it } from "vitest";
import { containsSecretValue } from "./dashboard";
import { parseSecretAction, secretsHref } from "./secrets";
import { filterManagedSecrets, summarizeSecrets, type ManagedSecret } from "./secrets-data";

const SAMPLE: ManagedSecret[] = [
  {
    id: "sec-amer-prd-app",
    name: "app-runtime-credentials",
    namespace: "prd",
    provider: "AWS",
    region: "AMER",
    environment: "PRD",
    account: "prod-amer",
    status: "Due soon",
    lastRotated: "48d ago",
    nextDue: "12d",
    lastValidated: "2h ago",
    history: [
      {
        at: "48d ago",
        actor: "rotation-scheduler",
        action: "Rotate",
        result: "Succeeded",
        detail: "Production rotation recorded without values",
      },
    ],
  },
];

describe("secrets management", () => {
  it("never includes secret values in catalog or history", () => {
    for (const secret of SAMPLE) {
      expect("value" in secret).toBe(false);
      expect(containsSecretValue(secret.name)).toBe(false);
      expect(containsSecretValue(secret.history[0]?.detail ?? "")).toBe(false);
    }
  });

  it("filters by provider, region, account, and environment hierarchy", () => {
    const prdAmer = filterManagedSecrets(SAMPLE, {
      provider: "AWS",
      region: "AMER",
      account: "prod-amer",
      environment: "PRD",
    });
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
    const summary = summarizeSecrets(SAMPLE);
    expect(summary.prd).toBe(1);
  });
});
