import { describe, expect, it } from "vitest";
import { cloudOpsApi } from "./api/client";
import { ONBOARDING_STEPS, readinessTone } from "./platform";

describe("platform readiness tone", () => {
  it("marks failed validation as critical", () => {
    expect(readinessTone("VALIDATION_FAILED")).toBe("critical");
    expect(readinessTone("CREDENTIAL_MISSING")).toBe("critical");
    expect(readinessTone("DISCOVERY_PENDING")).toBe("warning");
    expect(readinessTone("NOT_CONFIGURED")).toBe("warning");
    expect(readinessTone("ACTIVE")).toBeUndefined();
    expect(readinessTone("READY")).toBeUndefined();
    expect(readinessTone("DISABLED")).toBeUndefined();
  });
});

describe("empty-database onboarding", () => {
  it("lists the six setup steps and keeps demo data off the default path", () => {
    expect(ONBOARDING_STEPS).toEqual([
      "Configure Cloud Provider",
      "Configure Cloud Account",
      "Create Environment",
      "Configure Authentication",
      "Validate Connection",
      "Discover Resources",
    ]);
  });
});

describe("administration API client", () => {
  it("exposes provider, account, environment, credential, and discovery actions", () => {
    expect(cloudOpsApi.createProvider).toBeTypeOf("function");
    expect(cloudOpsApi.createAccount).toBeTypeOf("function");
    expect(cloudOpsApi.createEnvironment).toBeTypeOf("function");
    expect(cloudOpsApi.createCredential).toBeTypeOf("function");
    expect(cloudOpsApi.validateAccount).toBeTypeOf("function");
    expect(cloudOpsApi.discoverEnvironment).toBeTypeOf("function");
    expect(cloudOpsApi.environmentCertificateScan).toBeTypeOf("function");
    expect(cloudOpsApi.environmentHealthScan).toBeTypeOf("function");
    expect(cloudOpsApi.discoveryJobs).toBeTypeOf("function");
    expect(cloudOpsApi.platformStatus).toBeTypeOf("function");
  });
});
