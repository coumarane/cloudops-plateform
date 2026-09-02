import { describe, expect, it } from "vitest";
import { catalogHref, parseCatalogFilters } from "./catalog";
import { containsSecretValue } from "./dashboard";
import { PLACEHOLDER_SECTIONS } from "./navigation";

describe("remaining console catalogs", () => {
  it("implements every primary nav route", () => {
    expect(PLACEHOLDER_SECTIONS).toEqual([]);
  });

  it("builds catalog URLs for dashboard deep-links", () => {
    expect(
      catalogHref("/clusters", {
        provider: "AWS",
        region: "EMEA",
        environment: "UAT",
        selected: "eu-west-1-uat-k8s",
      }),
    ).toBe("/clusters?provider=aws&region=emea&environment=uat&selected=eu-west-1-uat-k8s");
    expect(parseCatalogFilters({ provider: "alibaba", region: "china", environment: "prd" })).toEqual({
      provider: "Alibaba",
      region: "China",
      environment: "PRD",
      selected: null,
    });
  });

  it("never treats catalog identifiers as secret values", () => {
    expect(containsSecretValue("eu-west-1-uat-k8s")).toBe(false);
    expect(containsSecretValue("ingress-tls-wildcard")).toBe(false);
  });
});
