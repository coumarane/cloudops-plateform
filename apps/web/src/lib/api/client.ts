import { deleteJson, getJson, getList, postJson, postJsonBody, putJsonBody, type ListResponse, type ScopeQuery } from "./http";
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
import type {
  GithubOrganization,
  GithubOverview,
  GithubRepository,
  GithubSecret,
  GithubVariable,
  GithubWorkflow,
  GithubWorkflowJob,
  GithubWorkflowRun,
} from "@/lib/github";
import { githubQuery } from "@/lib/github";
import type { Pipeline, PipelineOverview, PipelineRun, PipelineStage, PipelineJob } from "@/lib/pipelines";
import { pipelineQuery } from "@/lib/pipelines";
import type { HealthApplication, HealthIncident, HealthOverview, HealthResource, HealthTimelineEvent } from "@/lib/health";
import type {
  AlertListResponse,
  AlertRoutingRule,
  MaintenanceWindow,
  ManagedAlert,
  NotificationDestination,
  NotificationPolicy,
} from "@/lib/alerts";

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
  healthOverview: (signal?: AbortSignal) => getJson<HealthOverview>("/health/overview", undefined, signal),
  healthApplications: (query?: Record<string, string>, signal?: AbortSignal) =>
    getJson<{ items: HealthApplication[]; lastSynced: string }>(
      `/health/applications${pipelineQuery(query)}`,
      undefined,
      signal,
    ),
  healthApplication: (id: string, signal?: AbortSignal) => getJson<HealthApplication>(`/health/applications/${id}`, undefined, signal),
  healthApplicationHistory: (id: string, signal?: AbortSignal) =>
    getJson<{ items: Array<{ id: string; status: string; summary: string; createdAt: string }>; timeline: HealthTimelineEvent[] }>(
      `/health/applications/${id}/history`,
      undefined,
      signal,
    ),
  healthResources: (query?: Record<string, string>, signal?: AbortSignal) =>
    getJson<{ items: HealthResource[]; lastSynced: string }>(`/health/resources${pipelineQuery(query)}`, undefined, signal),
  healthIncidents: (query?: Record<string, string>, signal?: AbortSignal) =>
    getJson<{ items: HealthIncident[]; lastSynced: string }>(`/health/incidents${pipelineQuery(query)}`, undefined, signal),
  healthIncident: (id: string, signal?: AbortSignal) => getJson<HealthIncident>(`/health/incidents/${id}`, undefined, signal),
  acknowledgeIncident: (id: string, signal?: AbortSignal) => postJson<HealthIncident>(`/health/incidents/${id}/acknowledge`, signal),
  runHealthCheck: (id: string, signal?: AbortSignal) => postJson<{ queued: boolean }>(`/health/checks/${id}/run`, signal),
  deployments: (scope?: ScopeQuery, signal?: AbortSignal) => getList<RunRecord>("/deployments", scope, signal),
  pipelines: (scope?: ScopeQuery, signal?: AbortSignal) => getList<RunRecord>("/pipeline-runs", scope, signal),
  pipelineOverview: (signal?: AbortSignal) => getJson<PipelineOverview>("/pipelines/overview", undefined, signal),
  pipelineDefinitions: (query?: Record<string, string>, signal?: AbortSignal) =>
    getJson<{ items: Pipeline[]; lastSynced: string }>(`/pipelines${pipelineQuery(query)}`, undefined, signal),
  pipelineDefinition: (id: string, signal?: AbortSignal) => getJson<Pipeline>(`/pipelines/${id}`, undefined, signal),
  pipelineRunsFor: (id: string, signal?: AbortSignal) => getList<PipelineRun>(`/pipelines/${id}/runs`, undefined, signal),
  pipelineRun: (id: string, signal?: AbortSignal) => getJson<PipelineRun>(`/pipeline-runs/${id}`, undefined, signal),
  pipelineRunStages: (id: string, signal?: AbortSignal) => getList<PipelineStage>(`/pipeline-runs/${id}/stages`, undefined, signal),
  pipelineRunJobs: (id: string, signal?: AbortSignal) => getList<PipelineJob>(`/pipeline-runs/${id}/jobs`, undefined, signal),
  triggerPipelineSync: (signal?: AbortSignal) => postJson<{ queued: boolean; jobs: RunRecord[] }>("/pipelines/sync", signal),
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
  scmOverview: (signal?: AbortSignal) => getJson<GithubOverview>("/scm/overview", undefined, signal),
  scmOrganizations: (signal?: AbortSignal) => getList<GithubOrganization>("/scm/organizations", undefined, signal),
  scmRepositories: (signal?: AbortSignal) => getList<GithubRepository>("/scm/repositories", undefined, signal),
  scmRepository: (id: string, signal?: AbortSignal) => getJson<GithubRepository>(`/scm/repositories/${id}`, undefined, signal),
  scmRepositoryWorkflows: (id: string, signal?: AbortSignal) =>
    getList<GithubWorkflow>(`/scm/repositories/${id}/workflows`, undefined, signal),
  scmWorkflows: (signal?: AbortSignal) => getList<GithubWorkflow>("/scm/workflows", undefined, signal),
  scmWorkflow: (id: string, signal?: AbortSignal) => getJson<GithubWorkflow>(`/scm/workflows/${id}`, undefined, signal),
  scmWorkflowRuns: (id: string, signal?: AbortSignal) => getList<GithubWorkflowRun>(`/scm/workflows/${id}/runs`, undefined, signal),
  scmRun: (id: string, signal?: AbortSignal) => getJson<GithubWorkflowRun>(`/scm/workflow-runs/${id}`, undefined, signal),
  scmRunJobs: (id: string, signal?: AbortSignal) => getList<GithubWorkflowJob>(`/scm/workflow-runs/${id}/jobs`, undefined, signal),
  scmVariables: (query?: Record<string, string>, signal?: AbortSignal) =>
    getJson<ListResponse<GithubVariable>>(`/scm/variables${githubQuery(query)}`, undefined, signal),
  scmSecrets: (query?: Record<string, string>, signal?: AbortSignal) =>
    getJson<ListResponse<GithubSecret>>(`/scm/secrets${githubQuery(query)}`, undefined, signal),
  createGithubSecret: (body: Record<string, unknown>, signal?: AbortSignal) =>
    postJsonBody<GithubSecret>("/scm/secrets", body, signal),
  replaceGithubSecret: (id: string, body: Record<string, unknown>, signal?: AbortSignal) =>
    putJsonBody<GithubSecret>(`/scm/secrets/${id}`, body, signal),
  deleteGithubSecret: (id: string, body: Record<string, unknown>, signal?: AbortSignal) =>
    deleteJson<{ deleted: boolean }>(`/scm/secrets/${id}`, body, signal),
  createGithubVariable: (body: Record<string, unknown>, signal?: AbortSignal) =>
    postJsonBody<GithubVariable>("/scm/variables", body, signal),
  triggerGithubSync: (signal?: AbortSignal) => postJson<{ queued: boolean; jobs: RunRecord[] }>("/scm/sync", signal),
  alerts: (scope?: ScopeQuery, signal?: AbortSignal) => getList<OperationalAlert>("/alerts", scope, signal),
  managedAlerts: (query?: Record<string, string>, signal?: AbortSignal) =>
    getJson<AlertListResponse>(`/alerts${pipelineQuery(query)}`, undefined, signal),
  managedAlert: (id: string, signal?: AbortSignal) => getJson<ManagedAlert>(`/alerts/${id}`, undefined, signal),
  acknowledgeAlert: (id: string, comment: string, signal?: AbortSignal) =>
    postJsonBody<ManagedAlert>(`/alerts/${id}/acknowledge`, { comment }, signal),
  resolveAlert: (id: string, comment: string, signal?: AbortSignal) =>
    postJsonBody<ManagedAlert>(`/alerts/${id}/resolve`, { comment }, signal),
  suppressAlert: (id: string, reason: string, signal?: AbortSignal) =>
    postJsonBody<ManagedAlert>(`/alerts/${id}/suppress`, { reason }, signal),
  notificationDestinations: (signal?: AbortSignal) => getList<NotificationDestination>("/notification-destinations", undefined, signal),
  createNotificationDestination: (body: Record<string, unknown>, signal?: AbortSignal) =>
    postJsonBody<NotificationDestination>("/notification-destinations", body, signal),
  testNotificationDestination: (id: string, signal?: AbortSignal) =>
    postJson<{ id: string; status: string; externalMessageId: string; detail: string }>(`/notification-destinations/${id}/test`, signal),
  notificationPolicies: (signal?: AbortSignal) => getList<NotificationPolicy>("/notification-policies", undefined, signal),
  alertRoutingRules: (signal?: AbortSignal) => getList<AlertRoutingRule>("/alert-routing-rules", undefined, signal),
  maintenanceWindows: (signal?: AbortSignal) => getList<MaintenanceWindow>("/maintenance-windows", undefined, signal),
  createMaintenanceWindow: (body: Record<string, unknown>, signal?: AbortSignal) =>
    postJsonBody<MaintenanceWindow>("/maintenance-windows", body, signal),
  auditEvents: (scope?: ScopeQuery, signal?: AbortSignal) => getList<AuditEvent>("/audit-events", scope, signal),
  dashboard: (scope?: ScopeQuery, signal?: AbortSignal) => getJson<DashboardSnapshot>("/dashboard", scope, signal),
  adminUsers: (signal?: AbortSignal) => getList<AdminUser>("/admin/users", undefined, signal),
  adminIntegrations: (signal?: AbortSignal) => getList<AdminIntegration>("/admin/integrations", undefined, signal),
};
