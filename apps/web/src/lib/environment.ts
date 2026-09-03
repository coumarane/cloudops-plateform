import { ENVIRONMENTS, type Environment, type Provider, type Region } from "./types";

export const ENVIRONMENT_TABS = [
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
] as const;

export type EnvironmentTab = (typeof ENVIRONMENT_TABS)[number];

export const ENVIRONMENT_TAB_LABELS: Record<EnvironmentTab, string> = {
  overview: "Overview",
  clusters: "Clusters",
  applications: "Applications",
  certificates: "Certificates",
  pipelines: "Pipelines",
  health: "Health",
  alerts: "Alerts",
  configuration: "Configuration",
  secrets: "Secrets",
  deployments: "Deployments",
  github: "GitHub",
  audit: "Audit",
};

export function providerToSlug(provider: Provider): string {
  return provider.toLowerCase();
}

export function regionToSlug(region: Region): string {
  return region.toLowerCase();
}

export function environmentToSlug(environment: Environment): string {
  return environment === "INT/TST" ? "int-tst" : environment.toLowerCase();
}

export function parseProvider(value: string): Provider | null {
  if (value === "aws") return "AWS";
  if (value === "alibaba") return "Alibaba";
  if (value === "azure") return "Azure";
  if (value === "gcp" || value === "google") return "GCP";
  return null;
}

export function parseRegion(value: string): Region | null {
  const map: Record<string, Region> = {
    amer: "AMER",
    emea: "EMEA",
    apac: "APAC",
    china: "China",
  };
  return map[value] ?? null;
}

export function parseEnvironment(value: string): Environment | null {
  if (value === "int-tst") return "INT/TST";
  const match = ENVIRONMENTS.find((environment) => environment.toLowerCase() === value);
  return match ?? null;
}

export function parseTab(value: string | null): EnvironmentTab {
  if (value && ENVIRONMENT_TABS.includes(value as EnvironmentTab)) {
    return value as EnvironmentTab;
  }
  return "overview";
}

export function environmentHref(
  provider: Provider,
  region: Region,
  environment: Environment,
  tab: EnvironmentTab = "overview",
): string {
  const base = `/environments/${providerToSlug(provider)}/${regionToSlug(region)}/${environmentToSlug(environment)}`;
  return tab === "overview" ? base : `${base}?tab=${tab}`;
}

export function isRegionForProvider(provider: Provider, region: Region): boolean {
  if (provider === "AWS") {
    return region === "AMER" || region === "EMEA" || region === "APAC";
  }
  return region === "China";
}
