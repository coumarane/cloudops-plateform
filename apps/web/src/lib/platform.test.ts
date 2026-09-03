import { readinessTone } from "./platform";

describe("platform readiness tone", () => {
  it("marks failed validation as critical", () => {
    expect(readinessTone("VALIDATION_FAILED")).toBe("critical");
    expect(readinessTone("CREDENTIAL_MISSING")).toBe("critical");
    expect(readinessTone("DISCOVERY_PENDING")).toBe("warning");
    expect(readinessTone("ACTIVE")).toBeUndefined();
  });
});
