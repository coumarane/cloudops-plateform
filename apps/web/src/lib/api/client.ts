import { getJson, getList, postJson, postJsonBody, type ListResponse, type ScopeQuery } from "./http";
import type {
  AccountRecord,
  AdminIntegration,
  AdminUser,
  ApplicationRecord,
  AuditEvent,
  CertificateRecord,
  ClusterHealthRecord,
  ClusterRecord,
  CredentialHistoryEvent,
  CredentialRecord,
  DashboardSnapshot,
  EnvironmentIdentity,
  EnvironmentRecord,
  HealthCheckRecord,
  OperationalAlert,
  ProviderRecord,
  RegionRecord,
  RunRecord,
  SecretRecord,
} from "@/lib/domain";

export type { ListResponse, ScopeQuery };

export const cloudOpsApi = {
  providers: (signal?: AbortSignal) => getList<ProviderRecord>("/providers", undefined, signal),
  regions: (scope?: ScopeQuery, signal?: AbortSignal) => getList<RegionRecord>("/regions", scope, signal),
  accounts: (scope?: ScopeQuery, signal?: AbortSignal) => getList<AccountRecord>("/accounts", scope, signal),
  environments: (scope?: ScopeQuery, signal?: AbortSignal) =>
    getList<EnvironmentIdentity>("/environments", scope, signal),
  environment: (provider: string, region: string, environment: string, signal?: AbortSignal) =>
    getJson<EnvironmentRecord & { lastSynced: string }>(
      `/environments/${provider}/${region}/${environment}`,
      undefined,
      signal,
    ),
  clusters: (scope?: ScopeQuery, signal?: AbortSignal) => getList<ClusterRecord>("/clusters", scope, signal),
  cluster: (id: string, signal?: AbortSignal) => getJson<ClusterRecord & { health?: ClusterHealthRecord | null }>(`/clusters/${id}`, undefined, signal),
  clusterHealth: (id: string, signal?: AbortSignal) => getJson<ClusterHealthRecord>(`/clusters/${id}/health`, undefined, signal),
  applications: (scope?: ScopeQuery, signal?: AbortSignal) =>
    getList<ApplicationRecord>("/applications", scope, signal),
  certificates: (scope?: ScopeQuery, signal?: AbortSignal) =>
    getList<CertificateRecord>("/certificates", scope, signal),
  certificate: (id: string, signal?: AbortSignal) =>
    getJson<CertificateRecord>(`/certificates/${id}`, undefined, signal),
  certificateHistory: (id: string, signal?: AbortSignal) =>
    getList<{ id: string; event: string; detail: string; createdAt: string }>(`/certificates/${id}/history`, undefined, signal),
  certificateAlerts: (id: string, signal?: AbortSignal) =>
    getList<{ id: string; kind: string; severity: string; status: string; domain: string }>(
      `/certificates/${id}/alerts`,
      undefined,
      signal,
    ),
  triggerCertificateDiscovery: (signal?: AbortSignal) => postJson<RunRecord>("/certificates/scan", signal),
  validateCertificate: (id: string, signal?: AbortSignal) => postJson<RunRecord>(`/certificates/${id}/validate`, signal),
  secrets: (scope?: ScopeQuery, signal?: AbortSignal) => getList<SecretRecord>("/secrets", scope, signal),
  credentials: (scope?: ScopeQuery, signal?: AbortSignal) => getList<CredentialRecord>("/credentials", scope, signal),
  credential: (id: string, signal?: AbortSignal) => getJson<CredentialRecord>(`/credentials/${id}`, undefined, signal),
  createCredential: (body: Record<string, unknown>, signal?: AbortSignal) =>
    postJsonBody<CredentialRecord>("/credentials", body, signal),
  updateCredential: (id: string, body: Record<string, unknown>, signal?: AbortSignal) =>
    postJsonBody<CredentialRecord>(`/credentials/${id}`, body, signal),
  replaceCredential: (id: string, body: Record<string, unknown>, signal?: AbortSignal) =>
    postJsonBody<CredentialRecord>(`/credentials/${id}/replace`, body, signal),
  validateCredential: (id: string, signal?: AbortSignal) =>
    postJson<{ queued: boolean; jobId: string; credentialId: string; status: string; detail: string }>(
      `/credentials/${id}/validate`,
      signal,
    ),
  credentialHistory: (id: string, signal?: AbortSignal) =>
    getList<CredentialHistoryEvent>(`/credentials/${id}/history`, undefined, signal),
  credentialValidations: (id: string, signal?: AbortSignal) =>
    getList<{ id: string; success: boolean; status: string; providerAccount: string; createdAt: string }>(
      `/credentials/${id}/validations`,
      undefined,
      signal,
    ),
  healthChecks: (scope?: ScopeQuery, signal?: AbortSignal) =>
    getList<HealthCheckRecord>("/health-checks", scope, signal),
  deployments: (scope?: ScopeQuery, signal?: AbortSignal) => getList<RunRecord>("/deployments", scope, signal),
  pipelines: (scope?: ScopeQuery, signal?: AbortSignal) => getList<RunRecord>("/pipelines", scope, signal),
  jobs: (scope?: ScopeQuery, signal?: AbortSignal) => getList<RunRecord>("/jobs", scope, signal),
  triggerClusterDiscovery: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/aws/cluster-discovery", signal),
  triggerHealthScan: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/aws/health-scan", signal),
  triggerCertificateScan: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/aws/certificate-scan", signal),
  triggerAlibabaAccountValidation: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/alibaba/account-validation", signal),
  triggerAlibabaClusterDiscovery: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/alibaba/cluster-discovery", signal),
  triggerAlibabaHealthScan: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/alibaba/health-scan", signal),
  triggerAlibabaCertificateDiscovery: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/alibaba/certificate-discovery", signal),
  triggerAlibabaCertificateExpiryScan: (signal?: AbortSignal) => postJson<RunRecord>("/jobs/alibaba/certificate-expiry-scan", signal),
  githubRuns: (scope?: ScopeQuery, signal?: AbortSignal) => getList<RunRecord>("/github-runs", scope, signal),
  alerts: (scope?: ScopeQuery, signal?: AbortSignal) => getList<OperationalAlert>("/alerts", scope, signal),
  auditEvents: (scope?: ScopeQuery, signal?: AbortSignal) => getList<AuditEvent>("/audit-events", scope, signal),
  dashboard: (scope?: ScopeQuery, signal?: AbortSignal) => getJson<DashboardSnapshot>("/dashboard", scope, signal),
  adminUsers: (signal?: AbortSignal) => getList<AdminUser>("/admin/users", undefined, signal),
  adminIntegrations: (signal?: AbortSignal) => getList<AdminIntegration>("/admin/integrations", undefined, signal),
};
