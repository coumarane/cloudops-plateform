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

export const EXPIRY_FILTERS = ["healthy", "warning", "critical", "urgent", "expired"] as const;

export function certificatesHref(filters?: {
  provider?: Provider;
  region?: Region;
  environment?: Environment;
  certificate?: string;
  status?: string;
  expiresWithinDays?: number;
  sort?: string;
}): string {
  const params = new URLSearchParams();
  if (filters?.provider) params.set("provider", providerToSlug(filters.provider));
  if (filters?.region) params.set("region", regionToSlug(filters.region));
  if (filters?.environment) params.set("environment", environmentToSlug(filters.environment));
  if (filters?.certificate) params.set("certificate", filters.certificate);
  if (filters?.status) params.set("status", filters.status);
  if (filters?.expiresWithinDays) params.set("expires_within_days", String(filters.expiresWithinDays));
  if (filters?.sort) params.set("sort", filters.sort);
  const query = params.toString();
  return query ? `/certificates?${query}` : "/certificates";
}

export function parseCertificatesFilters(search: {
  provider?: string;
  region?: string;
  environment?: string;
  certificate?: string;
  status?: string;
  expires_within_days?: string;
  sort?: string;
}) {
  const expires = search.expires_within_days ? Number(search.expires_within_days) : null;
  return {
    provider: search.provider ? parseProvider(search.provider) : null,
    region: search.region ? parseRegion(search.region) : null,
    environment: search.environment ? parseEnvironment(search.environment) : null,
    certificate: search.certificate || null,
    status: search.status || null,
    expiresWithinDays: Number.isFinite(expires) ? expires : null,
    sort: search.sort || null,
  };
}

export function sourceLabel(source?: string) {
  switch ((source || "").toLowerCase()) {
    case "acm":
    case "aws":
      return "ACM";
    case "cas":
    case "alibaba":
      return "CAS";
    case "kubernetes":
      return "Kubernetes TLS";
    case "https":
      return "HTTPS endpoint";
    case "mock":
      return "Catalog";
    default:
      return source || "Catalog";
  }
}
