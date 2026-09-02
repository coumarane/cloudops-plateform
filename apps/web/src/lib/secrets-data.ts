import { assertNoSecretValues, isProductionEnvironment } from "./dashboard";
import { getEnvironmentIdentity, listEnvironmentIdentities } from "./environment-data";
import type { SecretRotationStatus } from "./secrets";
import type { Environment, Provider, Region } from "./types";

export type SecretHistoryEvent = {
  at: string;
  actor: string;
  action: "Update" | "Rotate" | "Validate";
  result: "Succeeded" | "Failed" | "Cancelled";
  detail: string;
};

export type ManagedSecret = {
  id: string;
  name: string;
  namespace: string;
  provider: Provider;
  region: Region;
  environment: Environment;
  account: string;
  status: SecretRotationStatus;
  lastRotated: string;
  nextDue: string;
  lastValidated: string;
  history: SecretHistoryEvent[];
};

function identity(provider: Provider, region: Region, environment: Environment) {
  return getEnvironmentIdentity(provider, region, environment);
}

function history(
  events: SecretHistoryEvent[],
): SecretHistoryEvent[] {
  return events;
}

export const MANAGED_SECRETS: ManagedSecret[] = [
  {
    id: "sec-emea-uat-db",
    name: "db-credentials-finance",
    namespace: "finance-uat",
    ...pickScope("AWS", "EMEA", "UAT"),
    status: "Overdue",
    lastRotated: "96d ago",
    nextDue: "Overdue 12d",
    lastValidated: "1d ago",
    history: history([
      {
        at: "12d ago",
        actor: "rotation-scheduler",
        action: "Rotate",
        result: "Failed",
        detail: "Window missed; value never displayed",
      },
      {
        at: "96d ago",
        actor: "ops@cloudops.local",
        action: "Rotate",
        result: "Succeeded",
        detail: "Vault rotation completed",
      },
      {
        at: "1d ago",
        actor: "validator",
        action: "Validate",
        result: "Succeeded",
        detail: "Checksum verified in vault",
      },
    ]),
  },
  {
    id: "sec-amer-uat-app",
    name: "app-runtime-credentials",
    namespace: "uat",
    ...pickScope("AWS", "AMER", "UAT"),
    status: "Overdue",
    lastRotated: "80d ago",
    nextDue: "Overdue 5d",
    lastValidated: "6h ago",
    history: history([
      {
        at: "80d ago",
        actor: "ops@cloudops.local",
        action: "Update",
        result: "Succeeded",
        detail: "Metadata updated; material stays in vault",
      },
    ]),
  },
  {
    id: "sec-amer-prd-app",
    name: "app-runtime-credentials",
    namespace: "prd",
    ...pickScope("AWS", "AMER", "PRD"),
    status: "Due soon",
    lastRotated: "48d ago",
    nextDue: "12d",
    lastValidated: "2h ago",
    history: history([
      {
        at: "48d ago",
        actor: "rotation-scheduler",
        action: "Rotate",
        result: "Succeeded",
        detail: "Production rotation recorded without values",
      },
      {
        at: "2h ago",
        actor: "validator",
        action: "Validate",
        result: "Succeeded",
        detail: "Vault health check passed",
      },
    ]),
  },
  {
    id: "sec-amer-prd-payments",
    name: "db-credentials-payments",
    namespace: "payments-prd",
    ...pickScope("AWS", "AMER", "PRD"),
    status: "OK",
    lastRotated: "18d ago",
    nextDue: "42d",
    lastValidated: "2h ago",
    history: history([
      {
        at: "18d ago",
        actor: "ops@cloudops.local",
        action: "Rotate",
        result: "Succeeded",
        detail: "PRD rotation confirmed in vault",
      },
    ]),
  },
  {
    id: "sec-amer-prd-github",
    name: "github-deploy-token",
    namespace: "cicd-prd",
    ...pickScope("AWS", "AMER", "PRD"),
    status: "OK",
    lastRotated: "9d ago",
    nextDue: "81d",
    lastValidated: "6h ago",
    history: history([
      {
        at: "9d ago",
        actor: "github-sync",
        action: "Rotate",
        result: "Succeeded",
        detail: "Token reference rotated; value never stored here",
      },
    ]),
  },
  {
    id: "sec-china-prd-app",
    name: "app-runtime-credentials",
    namespace: "prd",
    ...pickScope("Alibaba", "China", "PRD"),
    status: "Due soon",
    lastRotated: "86d ago",
    nextDue: "4d",
    lastValidated: "3h ago",
    history: history([
      {
        at: "86d ago",
        actor: "ops@cloudops.local",
        action: "Rotate",
        result: "Succeeded",
        detail: "ACK production rotation completed",
      },
    ]),
  },
  {
    id: "sec-emea-npd-sync",
    name: "data-sync-credentials",
    namespace: "npd",
    ...pickScope("AWS", "EMEA", "NPD"),
    status: "OK",
    lastRotated: "22d ago",
    nextDue: "38d",
    lastValidated: "8h ago",
    history: history([
      {
        at: "22d ago",
        actor: "pipeline-bot",
        action: "Rotate",
        result: "Succeeded",
        detail: "NPD vault rotation recorded",
      },
    ]),
  },
  {
    id: "sec-amer-int-auth",
    name: "auth-build-credentials",
    namespace: "int-tst",
    ...pickScope("AWS", "AMER", "INT/TST"),
    status: "OK",
    lastRotated: "11d ago",
    nextDue: "49d",
    lastValidated: "4h ago",
    history: history([
      {
        at: "11d ago",
        actor: "github-sync",
        action: "Rotate",
        result: "Succeeded",
        detail: "Non-production rotation completed",
      },
    ]),
  },
];

function pickScope(provider: Provider, region: Region, environment: Environment) {
  const scope = identity(provider, region, environment);
  return {
    provider,
    region,
    environment,
    account: scope.account,
  };
}

export function listSecretAccounts(): string[] {
  return Array.from(new Set(listEnvironmentIdentities().map((item) => item.account))).sort();
}

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

export function managedSecretStrings(secret: ManagedSecret): string[] {
  return [
    secret.name,
    secret.namespace,
    secret.account,
    secret.status,
    secret.lastRotated,
    secret.nextDue,
    secret.lastValidated,
    ...secret.history.flatMap((event) => [event.at, event.actor, event.action, event.result, event.detail]),
  ];
}

function assertSecretsSafe(): void {
  assertNoSecretValues(MANAGED_SECRETS.flatMap(managedSecretStrings));
}

assertSecretsSafe();
