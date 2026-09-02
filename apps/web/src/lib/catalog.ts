import {
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  providerToSlug,
  regionToSlug,
} from "./environment";
import type { Environment, Provider, Region } from "./types";

export type CatalogFilters = {
  provider: Provider | null;
  region: Region | null;
  environment: Environment | null;
  selected: string | null;
};

export function catalogHref(
  path: string,
  filters?: {
    provider?: Provider;
    region?: Region;
    environment?: Environment;
    selected?: string;
  },
): string {
  const params = new URLSearchParams();
  if (filters?.provider) params.set("provider", providerToSlug(filters.provider));
  if (filters?.region) params.set("region", regionToSlug(filters.region));
  if (filters?.environment) params.set("environment", environmentToSlug(filters.environment));
  if (filters?.selected) params.set("selected", filters.selected);
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function parseCatalogFilters(search: {
  provider?: string;
  region?: string;
  environment?: string;
  selected?: string;
}): CatalogFilters {
  return {
    provider: search.provider ? parseProvider(search.provider) : null,
    region: search.region ? parseRegion(search.region) : null,
    environment: search.environment ? parseEnvironment(search.environment) : null,
    selected: search.selected || null,
  };
}

export function matchesCatalogFilters<T extends { provider: Provider; region: Region; environment: Environment }>(
  item: T,
  filters: {
    provider: Provider | "all";
    region: Region | "all";
    environment: Environment | "all";
  },
): boolean {
  if (filters.provider !== "all" && item.provider !== filters.provider) return false;
  if (filters.region !== "all" && item.region !== filters.region) return false;
  if (filters.environment !== "all" && item.environment !== filters.environment) return false;
  return true;
}
