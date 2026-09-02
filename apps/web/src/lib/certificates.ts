import {
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  providerToSlug,
  regionToSlug,
} from "./environment";
import type { Environment, Provider, Region } from "./types";

export const RENEWAL_STATUSES = ["OK", "Expiring", "Renewing", "Expired"] as const;
export type RenewalStatus = (typeof RENEWAL_STATUSES)[number];

export function certificatesHref(filters?: {
  provider?: Provider;
  region?: Region;
  environment?: Environment;
  certificate?: string;
}): string {
  const params = new URLSearchParams();
  if (filters?.provider) params.set("provider", providerToSlug(filters.provider));
  if (filters?.region) params.set("region", regionToSlug(filters.region));
  if (filters?.environment) params.set("environment", environmentToSlug(filters.environment));
  if (filters?.certificate) params.set("certificate", filters.certificate);
  const query = params.toString();
  return query ? `/certificates?${query}` : "/certificates";
}

export function parseCertificatesFilters(search: {
  provider?: string;
  region?: string;
  environment?: string;
  certificate?: string;
}) {
  return {
    provider: search.provider ? parseProvider(search.provider) : null,
    region: search.region ? parseRegion(search.region) : null,
    environment: search.environment ? parseEnvironment(search.environment) : null,
    certificate: search.certificate || null,
  };
}
