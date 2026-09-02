import { describe, expect, it } from "vitest";
import { toSearchParams } from "./http";

describe("typed API client query params", () => {
  it("omits all-scope filters and slugs INT/TST", () => {
    expect(toSearchParams({ provider: "all", region: "all", environment: "all" })).toBe("");
    expect(
      toSearchParams({
        provider: "AWS",
        region: "EMEA",
        environment: "INT/TST",
      }),
    ).toBe("?provider=aws&region=emea&environment=int-tst");
  });
});
