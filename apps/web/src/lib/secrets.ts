import {
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  providerToSlug,
  regionToSlug,
} from "./environment";
import type { Environment, Provider, Region } from "./types";

export const SECRET_ACTIONS = ["update", "rotate", "validate", "history"] as const;
export type SecretAction = (typeof SECRET_ACTIONS)[number];

export const SECRET_ACTION_LABELS: Record<SecretAction, string> = {
  update: "Update",
  rotate: "Rotate",
  validate: "Validate",
  history: "History",
};

export type SecretRotationStatus = "OK" | "Overdue" | "Due soon";

export function parseSecretAction(value: string | null): SecretAction | null {
  if (value && SECRET_ACTIONS.includes(value as SecretAction)) {
    return value as SecretAction;
  }
  return null;
}

export function secretsHref(filters?: {
  provider?: Provider;
  region?: Region;
  account?: string;
  environment?: Environment;
  secret?: string;
  action?: SecretAction;
}): string {
  const params = new URLSearchParams();
  if (filters?.provider) params.set("provider", providerToSlug(filters.provider));
  if (filters?.region) params.set("region", regionToSlug(filters.region));
  if (filters?.account) params.set("account", filters.account);
  if (filters?.environment) params.set("environment", environmentToSlug(filters.environment));
  if (filters?.secret) params.set("secret", filters.secret);
  if (filters?.action) params.set("action", filters.action);
  const query = params.toString();
  return query ? `/secrets?${query}` : "/secrets";
}

export function parseSecretsFilters(search: {
  provider?: string;
  region?: string;
  account?: string;
  environment?: string;
  secret?: string;
  action?: string;
}) {
  return {
    provider: search.provider ? parseProvider(search.provider) : null,
    region: search.region ? parseRegion(search.region) : null,
    account: search.account || null,
    environment: search.environment ? parseEnvironment(search.environment) : null,
    secret: search.secret || null,
    action: parseSecretAction(search.action ?? null),
  };
}
