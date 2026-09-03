export type Readiness =
  | "NOT_CONFIGURED"
  | "CREDENTIAL_MISSING"
  | "VALIDATION_FAILED"
  | "READY"
  | "DISCOVERY_PENDING"
  | "ACTIVE"
  | "DISABLED"
  | string;

export type ManagedProvider = {
  id: string;
  name: string;
  providerType: string;
  provider?: string;
  description: string;
  enabled: boolean;
  authStrategy: string;
  status: string;
  validationStatus: string;
  accounts: number;
  environments: number;
  clusters: number;
  lastValidatedAt?: string | null;
  lastSynchronizedAt?: string | null;
  identityAccount?: string;
  identityPrincipal?: string;
  errorCategory?: string;
  accountsDetail?: ManagedAccount[];
  environmentsDetail?: ManagedEnvironment[];
};

export type ManagedAccount = {
  id: string;
  name: string;
  account: string;
  provider: string;
  region: string;
  accountClass: string;
  accountClassCode?: string;
  cloudRegion: string;
  accountId?: string;
  roleArn?: string;
  ramRole?: string;
  authStrategy?: string;
  credentialRef?: string;
  enabled: boolean;
  managedProviderId?: string;
  readiness: Readiness;
  validationStatus?: string;
  lastValidatedAt?: string | null;
  identityAccount?: string;
  identityPrincipal?: string;
  hostedEnvironments: string[];
  clusters: number;
  environmentsDetail?: ManagedEnvironment[];
};

export type ManagedEnvironment = {
  id: string;
  name: string;
  code: string;
  provider: string;
  region: string;
  environment: string;
  account: string;
  accountId?: string;
  cloudRegion: string;
  enabled: boolean;
  readiness: Readiness;
  discoveryActive: boolean;
  clusters: number;
  lastSuccessfulScan?: string | null;
  lastError?: string | null;
};

export type DiscoveryJob = {
  id: string;
  job: string;
  provider: string;
  account: string;
  environment: string;
  type: string;
  started: string;
  finished?: string | null;
  status: string;
  resourcesFound: number;
  errors: number;
  detail: string;
  correlationId: string;
};

export type PlatformStatus = {
  demoMode: boolean;
  dataSource: string;
  bootstrapAdmin: boolean;
  onboarding: boolean;
  configuredProviders: number;
  providerStub: boolean;
};

export type PlatformSetting = {
  key: string;
  label: string;
  value: string;
  updatedAt: string;
  updatedBy: string;
};

export type ManagedApplication = {
  id: string;
  name: string;
  description: string;
  ownerTeam: string;
  repositoryId: string;
  pipelineId: string;
  enabled: boolean;
  bindings: Array<{
    id: string;
    environmentId: string;
    clusterId: string;
    namespace: string;
    workload: string;
    healthEndpoint: string;
  }>;
};

export function readinessTone(status: string): "critical" | "warning" | undefined {
  if (status === "VALIDATION_FAILED" || status === "CREDENTIAL_MISSING") return "critical";
  if (status === "NOT_CONFIGURED" || status === "DISCOVERY_PENDING") return "warning";
  return undefined;
}
