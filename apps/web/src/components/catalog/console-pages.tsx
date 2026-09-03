"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { NotificationsAdmin } from "@/components/admin/NotificationsAdmin";
import { AlibabaScanActions } from "@/components/catalog/AlibabaScanActions";
import { AwsScanActions } from "@/components/catalog/AwsScanActions";
import { CatalogBody, CatalogPanel, Kpi, KpiGrid, StatusChip } from "@/components/catalog/CatalogChrome";
import { ClusterHealthPanel } from "@/components/catalog/ClusterHealthPanel";
import { HierarchyFilters, useCatalogFilters } from "@/components/catalog/HierarchyFilters";
import { EnvBadge } from "@/components/status/EnvBadge";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import type { ListResponse } from "@/lib/api/http";
import { useResource } from "@/lib/api/use-resource";
import type { CatalogFilters } from "@/lib/catalog";
import { catalogHref } from "@/lib/catalog";
import { isProductionEnvironment } from "@/lib/dashboard";
import type {
  AccountRecord,
  AdminIntegration,
  AdminUser,
  ApplicationRecord,
  AuditEvent,
  ClusterRecord,
  HealthCheckRecord,
  OperationalAlert,
  RunRecord,
} from "@/lib/domain";
import { environmentHref, type EnvironmentTab } from "@/lib/environment";
import { countPrd, countProduction, summarizeStatus, type ScopeFilters } from "@/lib/fleet-data";

const BANNER =
  "Production scope is high-risk. Metadata only. Secret values are never displayed.";

function scopeOf(filters: ReturnType<typeof useCatalogFilters>): ScopeFilters {
  return {
    provider: filters.provider,
    region: filters.region,
    environment: filters.environment,
  };
}

function Shell<T>({
  title,
  subtitle,
  initial,
  loadingLabel,
  emptyLabel,
  emptyAction,
  loader,
  kpis,
  children,
  refreshKey = 0,
}: {
  title: string;
  subtitle: string;
  initial: CatalogFilters;
  loadingLabel: string;
  emptyLabel: string;
  emptyAction?: ReactNode;
  loader: (scope: ScopeFilters, signal: AbortSignal) => Promise<ListResponse<T>>;
  kpis: (rows: T[]) => ReactNode;
  children: (rows: T[], selected: string | null) => ReactNode;
  refreshKey?: number;
}) {
  const filters = useCatalogFilters(initial);
  const scope = scopeOf(filters);
  const state = useResource(
    (signal) => loader(scope, signal),
    [scope.provider, scope.region, scope.environment, refreshKey],
  );

  return (
    <CatalogBody
      title={title}
      subtitle={subtitle}
      environment={filters.environment}
      banner={BANNER}
      lastSynced={state.status === "success" ? state.data.lastSynced : undefined}
      filters={
        <HierarchyFilters
          provider={filters.provider}
          region={filters.region}
          environment={filters.environment}
          regions={filters.regions}
          setFilter={filters.setFilter}
        />
      }
      kpis={
        state.status === "success" ? (
          kpis(state.data.items)
        ) : (
          <p className="text-sm text-muted">
            {state.status === "error" ? "Summary unavailable." : "Loading summary…"}
          </p>
        )
      }
    >
      <QueryState
        state={state}
        loadingLabel={loadingLabel}
        emptyLabel={emptyLabel}
        emptyAction={emptyAction}
        isEmpty={(data) => data.items.length === 0}
      >
        {(data) => children(data.items, filters.selected)}
      </QueryState>
    </CatalogBody>
  );
}

function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            {headers.map((header) => (
              <th key={header} className="p-3">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function rowClass(selected: boolean, attention?: boolean) {
  if (selected) return "border-b border-outline bg-action/5 last:border-b-0";
  if (attention) return "border-b border-outline bg-warning/5 last:border-b-0";
  return "border-b border-outline last:border-b-0";
}

export function InfrastructureCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Infrastructure"
      subtitle="Provider → Region → Account across AWS EKS and Alibaba ACK."
      initial={initial}
      loadingLabel="Loading accounts…"
      emptyLabel="No cloud accounts configured."
      emptyAction={
        <Link href="/administration?section=accounts" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
          Add Account
        </Link>
      }
      loader={(scope, signal) => cloudOpsApi.accounts(scope, signal)}
      kpis={(rows: AccountRecord[]) => {
        const summary = summarizeStatus(rows, "accounts");
        return (
          <KpiGrid>
            <Kpi label="Accounts in scope" value={summary.inScope} />
            <Kpi label="Production accounts" value={summary.production ?? 0} tone={summary.production ? "prd" : undefined} />
            <Kpi label="Non-production accounts" value={summary.nonProduction ?? 0} />
            <Kpi label="AWS accounts" value={rows.filter((row) => row.provider === "AWS").length} />
            <Kpi label="Alibaba accounts" value={rows.filter((row) => row.provider === "Alibaba").length} />
          </KpiGrid>
        );
      }}
    >
      {(rows: AccountRecord[], selected) => (
        <CatalogPanel title="Account inventory" hint="Account class and cloud region only. Credentials stay in vault.">
          <Table headers={["Account", "Provider", "Region", "Class", "Cloud region", "Platform", "Environments", "Clusters"]}>
            {rows.map((row) => (
              <tr key={row.id} className={rowClass(row.id === selected, row.accountClass === "Production")}>
                <td className="p-3 font-mono text-xs font-semibold text-ink">{row.account}</td>
                <td className="p-3 text-muted">{row.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                <td className="p-3">
                  <StatusChip value={row.accountClass} />
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.cloudRegion}</td>
                <td className="p-3 text-muted">{row.platform}</td>
                <td className="p-3 text-muted">{row.environments}</td>
                <td className="p-3 text-muted">{row.clusters}</td>
              </tr>
            ))}
          </Table>
        </CatalogPanel>
      )}
    </Shell>
  );
}

export function ClustersCatalog({ initial }: { initial: CatalogFilters }) {
  const [nonce, setNonce] = useState(0);
  return (
    <Shell
      title="Clusters"
      subtitle="EKS and ACK clusters across AWS AMER, EMEA, APAC, and Alibaba China."
      initial={initial}
      loadingLabel="Loading clusters…"
      emptyLabel="No clusters discovered."
      emptyAction={
        <Link href="/administration?section=environments" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
          Discover Clusters
        </Link>
      }
      refreshKey={nonce}
      loader={(scope, signal) => cloudOpsApi.clusters(scope, signal)}
      kpis={(rows: ClusterRecord[]) => {
        const summary = summarizeStatus(rows, "clusters");
        return (
          <KpiGrid>
            <Kpi label="Clusters in scope" value={summary.inScope} />
            <Kpi label="Healthy" value={summary.healthy ?? 0} />
            <Kpi label="Degraded" value={summary.degraded ?? 0} tone={summary.degraded ? "warning" : undefined} />
            <Kpi label="Unreachable" value={summary.unreachable ?? 0} tone={summary.unreachable ? "critical" : undefined} />
            <Kpi label="PRD clusters" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(rows: ClusterRecord[], selected) => (
        <div className="space-y-4">
          <CatalogPanel title="Cluster fleet" hint="Cluster health and identity only. Kubeconfig material is never displayed.">
            <Table headers={["Cluster", "Platform", "Version", "Nodes", "Provider", "Region", "Environment", "Account", "Source", "Status", "Apps", "Monitoring"]}>
              {rows.map((row) => (
                <tr key={row.id} className={rowClass(row.id === selected, row.status !== "Healthy")}>
                  <td className="p-3 font-mono text-xs font-semibold text-ink">
                    <Link
                      href={catalogHref("/clusters", {
                        provider: row.provider,
                        region: row.region,
                        environment: row.environment,
                        selected: row.id,
                      })}
                      className="hover:underline"
                    >
                      {row.name}
                    </Link>
                  </td>
                  <td className="p-3 text-muted">{row.platform}</td>
                  <td className="p-3 text-muted">{row.version}</td>
                  <td className="p-3 text-muted">{row.nodes}</td>
                  <td className="p-3 text-muted">{row.provider}</td>
                  <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                  <td className="p-3">
                    <EnvBadge environment={row.environment} />
                  </td>
                  <td className="p-3 font-mono text-xs text-muted">{row.account}</td>
                  <td className="p-3 text-xs text-muted">{row.source === "mock" ? "Catalog" : `${({ aws: "AWS", alibaba: "Alibaba", azure: "Azure", gcp: "GCP" } as Record<string, string>)[row.source || ""] || "Cloud"} live`}</td>
                  <td className="p-3">
                    <StatusChip value={row.status} />
                  </td>
                  <td className="p-3 text-xs text-muted">{row.appsLabel}</td>
                  <td className="p-3">
                    <div className="flex flex-col gap-1">
                      <button
                        type="button"
                        className="text-left text-xs font-semibold text-action"
                        onClick={() =>
                          void cloudOpsApi
                            .updateClusterMonitoring(row.id, { monitoringEnabled: !(row.monitoringEnabled ?? true) })
                            .then(() => setNonce((value) => value + 1))
                        }
                      >
                        {(row.monitoringEnabled ?? true) ? "Disable monitoring" : "Enable monitoring"}
                      </button>
                      <button
                        type="button"
                        className="text-left text-xs font-semibold text-muted"
                        onClick={() =>
                          void cloudOpsApi.updateClusterMonitoring(row.id, { ignored: true }).then(() => setNonce((value) => value + 1))
                        }
                      >
                        Ignore
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </Table>
          </CatalogPanel>
          {selected ? <ClusterHealthPanel clusterId={selected} /> : null}
        </div>
      )}
    </Shell>
  );
}

export function ApplicationsCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Applications"
      subtitle="Workloads across AWS EKS and Alibaba ACK."
      initial={initial}
      loadingLabel="Loading applications…"
      emptyLabel="No applications configured."
      emptyAction={
        <Link href="/administration?section=applications" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
          Add Application
        </Link>
      }
      loader={(scope, signal) => cloudOpsApi.applications(scope, signal)}
      kpis={(rows: ApplicationRecord[]) => {
        const summary = summarizeStatus(rows, "apps");
        return (
          <KpiGrid>
            <Kpi label="Applications in scope" value={summary.inScope} />
            <Kpi label="Healthy" value={summary.healthy ?? 0} />
            <Kpi label="Degraded" value={summary.degraded ?? 0} tone={summary.degraded ? "warning" : undefined} />
            <Kpi label="Production apps" value={countProduction(rows)} tone={countProduction(rows) > 0 ? "prd" : undefined} />
            <Kpi label="PRD apps" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(rows: ApplicationRecord[], selected) => (
        <CatalogPanel title="Application catalog" hint="Replica and issue state only. Runtime secrets are never displayed.">
          <Table headers={["Application", "Namespace", "Replicas", "Health", "Source control", "Pipeline", "Workflow", "Issue", "Provider", "Region", "Environment", "Cluster"]}>
            {rows.map((row) => (
              <tr key={row.id} className={rowClass(row.id === selected, row.issue !== "Healthy")}>
                <td className="p-3 font-mono text-xs font-semibold text-ink">
                  <Link href={environmentHref(row.provider, row.region, row.environment, "applications")} className="hover:underline">
                    {row.name}
                  </Link>
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.namespace}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.replicas}</td>
                <td className="p-3">
                  <Link href={`/health-checks?app=${row.id}`} className="hover:underline">
                    <StatusChip value={row.healthStatus || row.issue} />
                  </Link>
                </td>
                <td className="p-3 font-mono text-xs text-muted">
                  {row.repository ? (
                    <Link href={row.repositoryId ? `/github?repo=${row.repositoryId}` : "/github"} className="hover:underline">
                      {row.repository}
                      {row.branch ? ` @ ${row.branch}` : ""}
                      {row.commitSha ? ` (${row.commitSha})` : ""}
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="p-3 font-mono text-xs text-muted">
                  {row.pipelineId ? (
                    <Link
                      href={row.latestPipelineRunId ? `/pipelines?run=${row.latestPipelineRunId}` : `/pipelines?pipeline=${row.pipelineId}`}
                      className="hover:underline"
                    >
                      {row.pipelineName || "pipeline"} ({row.latestPipelineStatus || row.pipelineProvider || "—"})
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="p-3 font-mono text-xs text-muted">
                  {row.workflowRunId ? (
                    <Link href={row.latestPipelineRunId ? `/pipelines?run=${row.latestPipelineRunId}` : `/github?run=${row.workflowRunId}`} className="hover:underline">
                      {row.workflow || "workflow"} ({row.latestWorkflowStatus || "—"})
                    </Link>
                  ) : (
                    row.workflow || "—"
                  )}
                </td>
                <td className="p-3">
                  <StatusChip value={row.issue} />
                </td>
                <td className="p-3 text-muted">{row.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                <td className="p-3">
                  <EnvBadge environment={row.environment} />
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.cluster}</td>
              </tr>
            ))}
          </Table>
        </CatalogPanel>
      )}
    </Shell>
  );
}

export function HealthChecksCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Health Checks"
      subtitle="Probe status for clusters and workloads. Private keys are never displayed."
      initial={initial}
      loadingLabel="Loading health checks…"
      emptyLabel="No health checks in the current hierarchy filter."
      loader={(scope, signal) => cloudOpsApi.healthChecks(scope, signal)}
      kpis={(rows: HealthCheckRecord[]) => {
        const summary = summarizeStatus(rows, "health");
        return (
          <KpiGrid>
            <Kpi label="Checks in scope" value={summary.inScope} />
            <Kpi label="Passing" value={summary.passing ?? 0} />
            <Kpi label="Warning" value={summary.warning ?? 0} tone={summary.warning ? "warning" : undefined} />
            <Kpi label="Failing" value={summary.failing ?? 0} tone={summary.failing ? "critical" : undefined} />
            <Kpi label="PRD checks" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(rows: HealthCheckRecord[], selected) => (
        <CatalogPanel title="Health catalog" hint="Probe results only. Secret values are never displayed.">
          <Table headers={["Check", "Target", "Type", "Status", "Last run", "Provider", "Region", "Environment", "Cluster"]}>
            {rows.map((row) => (
              <tr key={row.id} className={rowClass(row.id === selected, row.status !== "Passing")}>
                <td className="p-3 font-mono text-xs font-semibold text-ink">{row.name}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.target}</td>
                <td className="p-3 text-muted">{row.checkType}</td>
                <td className="p-3">
                  <StatusChip value={row.status} />
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.lastRun}</td>
                <td className="p-3 text-muted">{row.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                <td className="p-3">
                  <EnvBadge environment={row.environment} />
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.cluster}</td>
              </tr>
            ))}
          </Table>
        </CatalogPanel>
      )}
    </Shell>
  );
}

function RunsCatalog({
  title,
  subtitle,
  tableTitle,
  hint,
  loader,
  headers,
  nameHeader,
  hrefTab,
  initial,
}: {
  title: string;
  subtitle: string;
  tableTitle: string;
  hint: string;
  loader: (scope: ScopeFilters, signal: AbortSignal) => Promise<ListResponse<RunRecord>>;
  headers: string[];
  nameHeader: string;
  hrefTab: EnvironmentTab;
  initial: CatalogFilters;
}) {
  return (
    <Shell
      title={title}
      subtitle={subtitle}
      initial={initial}
      loadingLabel={`Loading ${nameHeader.toLowerCase()}s…`}
      emptyLabel={`No ${nameHeader.toLowerCase()}s in the current hierarchy filter.`}
      loader={loader}
      kpis={(rows) => {
        const summary = summarizeStatus(rows, "runs");
        return (
          <KpiGrid>
            <Kpi label={`${nameHeader}s in scope`} value={summary.inScope} />
            <Kpi label="Succeeded" value={summary.succeeded ?? 0} />
            <Kpi label="Failed" value={summary.failed ?? 0} tone={summary.failed ? "critical" : undefined} />
            <Kpi label="Running" value={summary.running ?? 0} />
            <Kpi label={`PRD ${nameHeader.toLowerCase()}s`} value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(rows, selected) => (
        <CatalogPanel title={tableTitle} hint={hint}>
          <Table headers={headers}>
            {rows.map((row) => (
              <tr key={row.id} className={rowClass(row.id === selected, row.result === "Failed")}>
                <td className="p-3 font-mono text-xs font-semibold text-ink">
                  <Link href={environmentHref(row.provider, row.region, row.environment, hrefTab)} className="hover:underline">
                    {row.name}
                  </Link>
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.detail}</td>
                <td className="p-3">
                  <StatusChip value={row.result} />
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.age}</td>
                <td className="p-3 text-muted">{row.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                <td className="p-3">
                  <EnvBadge environment={row.environment} />
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.cluster}</td>
              </tr>
            ))}
          </Table>
        </CatalogPanel>
      )}
    </Shell>
  );
}

export function DeploymentsCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <RunsCatalog
      title="Deployments"
      subtitle="Rollouts across AWS EKS and Alibaba ACK."
      tableTitle="Deployment catalog"
      hint="Rollout result only. Images and secret values are never displayed."
      loader={(scope, signal) => cloudOpsApi.deployments(scope, signal)}
      headers={["Deployment", "Detail", "Result", "Age", "Provider", "Region", "Environment", "Cluster"]}
      nameHeader="Deployment"
      hrefTab="deployments"
      initial={initial}
    />
  );
}

export function PipelinesCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <RunsCatalog
      title="Pipelines"
      subtitle="DevOps pipeline runs. Secret values are never displayed."
      tableTitle="Pipeline catalog"
      hint="Stage result only. Pipeline secrets are never displayed."
      loader={(scope, signal) => cloudOpsApi.pipelines(scope, signal)}
      headers={["Pipeline", "Stage", "Result", "Age", "Provider", "Region", "Environment", "Cluster"]}
      nameHeader="Pipeline"
      hrefTab="pipelines"
      initial={initial}
    />
  );
}

export function GitHubCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <RunsCatalog
      title="GitHub"
      subtitle="GitHub Actions workflow runs. GitHub secrets and tokens are never displayed."
      tableTitle="Workflow catalog"
      hint="Repository and result only. Tokens and GitHub secrets are never displayed."
      loader={(scope, signal) => cloudOpsApi.githubRuns(scope, signal)}
      headers={["Workflow", "Repository", "Result", "Age", "Provider", "Region", "Environment", "Cluster"]}
      nameHeader="Workflow"
      hrefTab="github"
      initial={initial}
    />
  );
}

export function JobsCatalog({ initial }: { initial: CatalogFilters }) {
  const [refreshKey, setRefreshKey] = useState(0);
  return (
    <Shell
      title="Jobs"
      subtitle="Platform scans and scheduled jobs. Secret values are never displayed."
      initial={initial}
      loadingLabel="Loading jobs…"
      emptyLabel="No jobs in the current hierarchy filter."
      refreshKey={refreshKey}
      loader={(scope, signal) => cloudOpsApi.jobs(scope, signal)}
      kpis={(rows) => {
        const summary = summarizeStatus(rows, "runs");
        return (
          <KpiGrid>
            <Kpi label="Jobs in scope" value={summary.inScope} />
            <Kpi label="Succeeded" value={summary.succeeded ?? 0} />
            <Kpi label="Failed" value={summary.failed ?? 0} tone={summary.failed ? "critical" : undefined} />
            <Kpi label="Running" value={summary.running ?? 0} />
            <Kpi label="PRD jobs" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(rows, selected) => (
        <div className="space-y-4">
          <AwsScanActions onQueued={() => setRefreshKey((value) => value + 1)} />
          <AlibabaScanActions onQueued={() => setRefreshKey((value) => value + 1)} />
          <CatalogPanel title="Job catalog" hint="Job result only. Secret values are never displayed.">
            <Table headers={["Job", "Kind", "Result", "Age", "Provider", "Region", "Environment", "Cluster"]}>
              {rows.map((row) => (
                <tr key={row.id} className={rowClass(row.id === selected, row.result === "Failed")}>
                  <td className="p-3 font-mono text-xs font-semibold text-ink">{row.name}</td>
                  <td className="p-3 font-mono text-xs text-muted">{row.kind ?? row.detail}</td>
                  <td className="p-3">
                    <StatusChip value={row.result} />
                  </td>
                  <td className="p-3 font-mono text-xs text-muted">{row.age}</td>
                  <td className="p-3 text-muted">{row.provider}</td>
                  <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                  <td className="p-3">
                    <EnvBadge environment={row.environment} />
                  </td>
                  <td className="p-3 font-mono text-xs text-muted">{row.cluster}</td>
                </tr>
              ))}
            </Table>
          </CatalogPanel>
        </div>
      )}
    </Shell>
  );
}

export function AlertsCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Alerts"
      subtitle="Open operational alerts across AWS AMER, EMEA, APAC, and Alibaba China."
      initial={initial}
      loadingLabel="Loading alerts…"
      emptyLabel="No alerts in the current hierarchy filter."
      loader={(scope, signal) => cloudOpsApi.alerts(scope, signal)}
      kpis={(rows: OperationalAlert[]) => {
        const summary = summarizeStatus(rows, "alerts");
        return (
          <KpiGrid>
            <Kpi label="Open alerts" value={summary.inScope} />
            <Kpi label="Critical" value={summary.critical ?? 0} tone={summary.critical ? "critical" : undefined} />
            <Kpi label="Warning" value={summary.warning ?? 0} tone={summary.warning ? "warning" : undefined} />
            <Kpi label="Info" value={summary.info ?? 0} />
            <Kpi label="PRD alerts" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(rows: OperationalAlert[], selected) => (
        <CatalogPanel title="Alert catalog" hint="Object names and severity only. Secret values are never displayed.">
          <Table headers={["Severity", "Title", "Object", "Age", "Provider", "Region", "Environment"]}>
            {rows.map((row) => (
              <tr key={row.id} className={rowClass(row.id === selected, row.severity !== "info")}>
                <td className="p-3">
                  <StatusChip value={row.severity} />
                </td>
                <td className="p-3">
                  <Link href={row.href} className="text-sm font-semibold text-ink hover:underline">
                    {row.title}
                  </Link>
                </td>
                <td className="p-3 font-mono text-xs text-muted">{row.objectName}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.age}</td>
                <td className="p-3 text-muted">{row.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                <td className="p-3">
                  <EnvBadge environment={row.environment} />
                </td>
              </tr>
            ))}
          </Table>
        </CatalogPanel>
      )}
    </Shell>
  );
}

export function AuditCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Audit"
      subtitle="Console and platform audit events. Secret values are never displayed."
      initial={initial}
      loadingLabel="Loading audit events…"
      emptyLabel="No audit events in the current hierarchy filter."
      loader={(scope, signal) => cloudOpsApi.auditEvents(scope, signal)}
      kpis={(rows: AuditEvent[]) => (
        <KpiGrid>
          <Kpi label="Events in scope" value={rows.length} />
          <Kpi label="Production events" value={countProduction(rows)} tone={countProduction(rows) > 0 ? "prd" : undefined} />
          <Kpi label="Non-production events" value={rows.length - countProduction(rows)} />
          <Kpi label="PRD events" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          <Kpi label="Actors" value={new Set(rows.map((row) => row.actor)).size} />
        </KpiGrid>
      )}
    >
      {(rows: AuditEvent[], selected) => (
        <CatalogPanel title="Audit log" hint="Actor, object, and result only. Secret values are never displayed.">
          <Table headers={["Event", "Actor", "Object", "Detail", "Age", "Provider", "Region", "Environment"]}>
            {rows.map((row) => (
              <tr key={row.id} className={rowClass(row.id === selected, isProductionEnvironment(row.environment))}>
                <td className="p-3 text-sm font-semibold text-ink">{row.event}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.actor}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.objectName}</td>
                <td className="p-3 text-xs text-muted">{row.detail}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.age}</td>
                <td className="p-3 text-muted">{row.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                <td className="p-3">
                  <EnvBadge environment={row.environment} />
                </td>
              </tr>
            ))}
          </Table>
        </CatalogPanel>
      )}
    </Shell>
  );
}

export function AdministrationCatalog({ initial }: { initial: CatalogFilters }) {
  const filters = useCatalogFilters(initial);
  const users = useResource((signal) => cloudOpsApi.adminUsers(signal), []);
  const integrations = useResource((signal) => cloudOpsApi.adminIntegrations(signal), []);

  return (
    <CatalogBody
      title="Administration"
      subtitle="Console access, roles, and cloud integrations. Secret values are never displayed."
      environment={filters.environment}
      lastSynced={users.status === "success" ? users.data.lastSynced : undefined}
      banner="Production change control is required for PRD mutations. Credentials and tokens stay in vault."
      filters={
        <HierarchyFilters
          provider={filters.provider}
          region={filters.region}
          environment={filters.environment}
          regions={filters.regions}
          setFilter={filters.setFilter}
        />
      }
      kpis={
        users.status === "success" && integrations.status === "success" ? (
          <KpiGrid>
            <Kpi label="Users" value={users.data.items.length} />
            <Kpi label="Integrations" value={integrations.data.items.length} />
            <Kpi
              label="Connected"
              value={integrations.data.items.filter((item: AdminIntegration) => item.status === "Connected").length}
            />
            <Kpi label="Production roles" value={1} tone="prd" />
            <Kpi label="Read-only auditors" value={1} />
          </KpiGrid>
        ) : (
          <p className="text-sm text-muted">Loading summary…</p>
        )
      }
    >
      <QueryState state={users} loadingLabel="Loading users…">
        {(data) => (
          <CatalogPanel title="Users" hint="Role and scope only. Passwords are never displayed.">
            <Table headers={["User", "Role", "Scope", "Last active"]}>
              {data.items.map((user: AdminUser) => (
                <tr key={user.id} className={rowClass(false, user.role === "Platform Admin")}>
                  <td className="p-3 font-mono text-xs font-semibold text-ink">{user.user}</td>
                  <td className="p-3 text-muted">{user.role}</td>
                  <td className="p-3 text-muted">{user.scope}</td>
                  <td className="p-3 font-mono text-xs text-muted">{user.lastActive}</td>
                </tr>
              ))}
            </Table>
          </CatalogPanel>
        )}
      </QueryState>
      <QueryState state={integrations} loadingLabel="Loading integrations…">
        {(data) => (
          <CatalogPanel title="Integrations" hint="Connection state only. Client secrets and tokens are never displayed.">
            <Table headers={["Integration", "Status", "Scope", "Note"]}>
              {data.items.map((item: AdminIntegration) => (
                <tr key={item.id} className={rowClass(false)}>
                  <td className="p-3 font-semibold text-ink">{item.name}</td>
                  <td className="p-3">
                    <StatusChip value={item.status} />
                  </td>
                  <td className="p-3 text-muted">{item.scope}</td>
                  <td className="p-3 text-xs text-muted">{item.note}</td>
                </tr>
              ))}
            </Table>
          </CatalogPanel>
        )}
      </QueryState>
      <NotificationsAdmin />
    </CatalogBody>
  );
}
