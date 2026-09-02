import { isProductionEnvironment } from "./dashboard";
import type { SecretRecord } from "./domain";
import type { Environment, Provider, Region } from "./types";

export type ManagedSecret = SecretRecord;

export function filterManagedSecrets(
  secrets: ManagedSecret[],
  filters: {
    provider: Provider | "all";
    region: Region | "all";
    account: string | "all";
    environment: Environment | "all";
  },
): ManagedSecret[] {
  return secrets.filter((secret) => {
    if (filters.provider !== "all" && secret.provider !== filters.provider) return false;
    if (filters.region !== "all" && secret.region !== filters.region) return false;
    if (filters.account !== "all" && secret.account !== filters.account) return false;
    if (filters.environment !== "all" && secret.environment !== filters.environment) return false;
    return true;
  });
}

export function summarizeSecrets(secrets: ManagedSecret[]) {
  return {
    inScope: secrets.length,
    overdue: secrets.filter((secret) => secret.status === "Overdue").length,
    dueSoon: secrets.filter((secret) => secret.status === "Due soon").length,
    production: secrets.filter((secret) => isProductionEnvironment(secret.environment)).length,
    prd: secrets.filter((secret) => secret.environment === "PRD").length,
  };
}

export function listSecretAccounts(secrets: ManagedSecret[]): string[] {
  return Array.from(new Set(secrets.map((item) => item.account))).sort();
}
