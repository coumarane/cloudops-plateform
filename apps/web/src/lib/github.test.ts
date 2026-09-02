import { describe, expect, it } from "vitest";
import { displayVariableValue } from "./github-data";
import { GITHUB_SECRET_MASK, githubHref, parseGithubFilters, shortSha } from "./github";

describe("GitHub console helpers", () => {
  it("builds workflow run links", () => {
    expect(githubHref({ run: "ghrun-1" })).toBe("/github?run=ghrun-1");
    expect(parseGithubFilters({ run: "ghrun-1" }).run).toBe("ghrun-1");
  });

  it("masks sensitive variables and never treats the mask as a secret assignment", () => {
    expect(
      displayVariableValue({
        id: "1",
        name: "DB_HOST",
        scope: "repository",
        repositoryId: "r",
        repository: "acme/app",
        organization: "acme",
        githubEnvironment: "",
        value: GITHUB_SECRET_MASK,
        sensitive: true,
      }),
    ).toBe(GITHUB_SECRET_MASK);
    expect(shortSha("abcdef123456")).toBe("abcdef1");
  });
});
