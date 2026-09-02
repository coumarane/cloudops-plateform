import { describe, expect, it } from "vitest";
import { openInProviderLabel, parsePipelineFilters, pipelineHref } from "./pipelines";

describe("pipeline helpers", () => {
  it("builds pipeline run links", () => {
    expect(pipelineHref({ run: "prun-1" })).toBe("/pipelines?run=prun-1");
    expect(openInProviderLabel("github-actions")).toBe("Open in GitHub");
    expect(openInProviderLabel("azure-devops")).toBe("Open in Azure DevOps");
  });

  it("parses pipeline search params", () => {
    const parsed = parsePipelineFilters({ pipeline: "pl-1", run: "prun-1", tab: "runs" });
    expect(parsed.pipeline).toBe("pl-1");
    expect(parsed.run).toBe("prun-1");
    expect(parsed.tab).toBe("runs");
  });
});
