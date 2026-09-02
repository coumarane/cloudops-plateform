"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { CatalogBody, CatalogPanel, Kpi, KpiGrid, StatusChip } from "@/components/catalog/CatalogChrome";
import { HierarchyFilters, useCatalogFilters } from "@/components/catalog/HierarchyFilters";
import { EnvBadge } from "@/components/status/EnvBadge";
import type { CatalogFilters } from "@/lib/catalog";
import { environmentHref, type EnvironmentTab } from "@/lib/environment";
import {
  ADMIN_INTEGRATIONS,
  ADMIN_USERS,
  countPrd,
  countProduction,
  FLEET_ALERTS,
  FLEET_APPLICATIONS,
  FLEET_AUDIT,
  FLEET_CLUSTERS,
  FLEET_DEPLOYMENTS,
  FLEET_GITHUB_RUNS,
  FLEET_HEALTH_CHECKS,
  FLEET_JOBS,
  FLEET_PIPELINES,
  filterByScope,
  filterInfrastructure,
  summarizeStatus,
  type ScopeFilters,
} from "@/lib/fleet-data";
import { isProductionEnvironment } from "@/lib/dashboard";

const BANNER =
  "Production scope is high-risk. Metadata only. Secret values are never displayed.";

function scopeOf(filters: ReturnType<typeof useCatalogFilters>): ScopeFilters {
  return {
    provider: filters.provider,
    region: filters.region,
    environment: filters.environment,
  };
}

function Shell({
  title,
  subtitle,
  initial,
  kpis,
  children,
}: {
  title: string;
  subtitle: string;
  initial: CatalogFilters;
  kpis: (scope: ScopeFilters) => ReactNode;
  children: (scope: ScopeFilters, selected: string | null) => ReactNode;
}) {
  const filters = useCatalogFilters(initial);
  const scope = scopeOf(filters);
  return (
    <CatalogBody
      title={title}
      subtitle={subtitle}
      environment={filters.environment}
      banner={BANNER}
      filters={
        <HierarchyFilters
          provider={filters.provider}
          region={filters.region}
          environment={filters.environment}
          regions={filters.regions}
          setFilter={filters.setFilter}
        />
      }
      kpis={kpis(scope)}
    >
      {children(scope, filters.selected)}
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

function Empty({ label }: { label: string }) {
  return <p className="p-4 text-sm text-muted">{label}</p>;
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
      kpis={(scope) => {
        const rows = filterInfrastructure(scope);
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
      {(scope, selected) => {
        const rows = filterInfrastructure(scope);
        return (
          <CatalogPanel title="Account inventory" hint="Account class and cloud region only. Credentials stay in vault.">
            {rows.length === 0 ? (
              <Empty label="No accounts in the current hierarchy filter." />
            ) : (
              <Table
                headers={[
                  "Account",
                  "Provider",
                  "Region",
                  "Class",
                  "Cloud region",
                  "Platform",
                  "Environments",
                  "Clusters",
                ]}
              >
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
            )}
          </CatalogPanel>
        );
      }}
    </Shell>
  );
}

export function ClustersCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Clusters"
      subtitle="EKS and ACK clusters across AWS AMER, EMEA, APAC, and Alibaba China."
      initial={initial}
      kpis={(scope) => {
        const rows = filterByScope(FLEET_CLUSTERS, scope);
        const summary = summarizeStatus(rows, "clusters");
        return (
          <KpiGrid>
            <Kpi label="Clusters in scope" value={summary.inScope} />
            <Kpi label="Healthy" value={summary.healthy ?? 0} />
            <Kpi label="Degraded" value={summary.degraded ?? 0} tone={summary.degraded ? "warning" : undefined} />
            <Kpi
              label="Unreachable"
              value={summary.unreachable ?? 0}
              tone={summary.unreachable ? "critical" : undefined}
            />
            <Kpi label="PRD clusters" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(scope, selected) => {
        const rows = filterByScope(FLEET_CLUSTERS, scope);
        return (
          <CatalogPanel title="Cluster fleet" hint="Cluster health and identity only. Kubeconfig material is never displayed.">
            {rows.length === 0 ? (
              <Empty label="No clusters in the current hierarchy filter." />
            ) : (
              <Table
                headers={[
                  "Cluster",
                  "Platform",
                  "Version",
                  "Nodes",
                  "Provider",
                  "Region",
                  "Environment",
                  "Account",
                  "Status",
                  "Apps",
                ]}
              >
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    className={rowClass(row.id === selected, row.status !== "Healthy")}
                  >
                    <td className="p-3 font-mono text-xs font-semibold text-ink">
                      <Link
                        href={environmentHref(row.provider, row.region, row.environment, "clusters")}
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
                    <td className="p-3">
                      <StatusChip value={row.status} />
                    </td>
                    <td className="p-3 text-xs text-muted">{row.appsLabel}</td>
                  </tr>
                ))}
              </Table>
            )}
          </CatalogPanel>
        );
      }}
    </Shell>
  );
}

export function ApplicationsCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Applications"
      subtitle="Workloads across AWS EKS and Alibaba ACK."
      initial={initial}
      kpis={(scope) => {
        const rows = filterByScope(FLEET_APPLICATIONS, scope);
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
      {(scope, selected) => {
        const rows = filterByScope(FLEET_APPLICATIONS, scope);
        return (
          <CatalogPanel title="Application catalog" hint="Replica and issue state only. Runtime secrets are never displayed.">
            {rows.length === 0 ? (
              <Empty label="No applications in the current hierarchy filter." />
            ) : (
              <Table
                headers={[
                  "Application",
                  "Namespace",
                  "Replicas",
                  "Issue",
                  "Provider",
                  "Region",
                  "Environment",
                  "Cluster",
                ]}
              >
                {rows.map((row) => (
                  <tr key={row.id} className={rowClass(row.id === selected, row.issue !== "Healthy")}>
                    <td className="p-3 font-mono text-xs font-semibold text-ink">
                      <Link
                        href={environmentHref(row.provider, row.region, row.environment, "applications")}
                        className="hover:underline"
                      >
                        {row.name}
                      </Link>
                    </td>
                    <td className="p-3 font-mono text-xs text-muted">{row.namespace}</td>
                    <td className="p-3 font-mono text-xs text-muted">{row.replicas}</td>
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
            )}
          </CatalogPanel>
        );
      }}
    </Shell>
  );
}

export function HealthChecksCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Health Checks"
      subtitle="Probe status for clusters and workloads. Private keys are never displayed."
      initial={initial}
      kpis={(scope) => {
        const rows = filterByScope(FLEET_HEALTH_CHECKS, scope);
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
      {(scope, selected) => {
        const rows = filterByScope(FLEET_HEALTH_CHECKS, scope);
        return (
          <CatalogPanel title="Health catalog" hint="Probe results only. Secret values are never displayed.">
            {rows.length === 0 ? (
              <Empty label="No health checks in the current hierarchy filter." />
            ) : (
              <Table
                headers={[
                  "Check",
                  "Target",
                  "Type",
                  "Status",
                  "Last run",
                  "Provider",
                  "Region",
                  "Environment",
                  "Cluster",
                ]}
              >
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
            )}
          </CatalogPanel>
        );
      }}
    </Shell>
  );
}

function RunsCatalog({
  title,
  subtitle,
  tableTitle,
  hint,
  rows,
  headers,
  nameHeader,
  hrefTab,
  initial,
}: {
  title: string;
  subtitle: string;
  tableTitle: string;
  hint: string;
  rows: typeof FLEET_DEPLOYMENTS;
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
      kpis={(scope) => {
        const scoped = filterByScope(rows, scope);
        const summary = summarizeStatus(scoped, "runs");
        return (
          <KpiGrid>
            <Kpi label={`${nameHeader}s in scope`} value={summary.inScope} />
            <Kpi label="Succeeded" value={summary.succeeded ?? 0} />
            <Kpi label="Failed" value={summary.failed ?? 0} tone={summary.failed ? "critical" : undefined} />
            <Kpi label="Running" value={summary.running ?? 0} />
            <Kpi label={`PRD ${nameHeader.toLowerCase()}s`} value={countPrd(scoped)} tone={countPrd(scoped) > 0 ? "prd" : undefined} />
          </KpiGrid>
        );
      }}
    >
      {(scope, selected) => {
        const scoped = filterByScope(rows, scope);
        return (
          <CatalogPanel title={tableTitle} hint={hint}>
            {scoped.length === 0 ? (
              <Empty label={`No ${nameHeader.toLowerCase()}s in the current hierarchy filter.`} />
            ) : (
              <Table headers={headers}>
                {scoped.map((row) => (
                  <tr key={row.id} className={rowClass(row.id === selected, row.result === "Failed")}>
                    <td className="p-3 font-mono text-xs font-semibold text-ink">
                      <Link
                        href={environmentHref(row.provider, row.region, row.environment, hrefTab)}
                        className="hover:underline"
                      >
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
            )}
          </CatalogPanel>
        );
      }}
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
      rows={FLEET_DEPLOYMENTS}
      headers={[
        "Deployment",
        "Detail",
        "Result",
        "Age",
        "Provider",
        "Region",
        "Environment",
        "Cluster",
      ]}
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
      rows={FLEET_PIPELINES}
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
      rows={FLEET_GITHUB_RUNS}
      headers={[
        "Workflow",
        "Repository",
        "Result",
        "Age",
        "Provider",
        "Region",
        "Environment",
        "Cluster",
      ]}
      nameHeader="Workflow"
      hrefTab="github"
      initial={initial}
    />
  );
}

export function JobsCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <RunsCatalog
      title="Jobs"
      subtitle="Scheduled and batch jobs. Secret values are never displayed."
      tableTitle="Job catalog"
      hint="Job result only. Secret values are never displayed."
      rows={FLEET_JOBS}
      headers={["Job", "Kind", "Result", "Age", "Provider", "Region", "Environment", "Cluster"]}
      nameHeader="Job"
      hrefTab="overview"
      initial={initial}
    />
  );
}

export function AlertsCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Alerts"
      subtitle="Open operational alerts across AWS AMER, EMEA, APAC, and Alibaba China."
      initial={initial}
      kpis={(scope) => {
        const rows = filterByScope(FLEET_ALERTS, scope);
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
      {(scope, selected) => {
        const rows = filterByScope(FLEET_ALERTS, scope);
        return (
          <CatalogPanel title="Alert catalog" hint="Object names and severity only. Secret values are never displayed.">
            {rows.length === 0 ? (
              <Empty label="No alerts in the current hierarchy filter." />
            ) : (
              <Table headers={["Severity", "Title", "Object", "Age", "Provider", "Region", "Environment"]}>
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    className={rowClass(row.id === selected, row.severity !== "info")}
                  >
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
            )}
          </CatalogPanel>
        );
      }}
    </Shell>
  );
}

export function AuditCatalog({ initial }: { initial: CatalogFilters }) {
  return (
    <Shell
      title="Audit"
      subtitle="Console and platform audit events. Secret values are never displayed."
      initial={initial}
      kpis={(scope) => {
        const rows = filterByScope(FLEET_AUDIT, scope);
        return (
          <KpiGrid>
            <Kpi label="Events in scope" value={rows.length} />
            <Kpi
              label="Production events"
              value={countProduction(rows)}
              tone={countProduction(rows) > 0 ? "prd" : undefined}
            />
            <Kpi label="Non-production events" value={rows.length - countProduction(rows)} />
            <Kpi label="PRD events" value={countPrd(rows)} tone={countPrd(rows) > 0 ? "prd" : undefined} />
            <Kpi label="Actors" value={new Set(rows.map((row) => row.actor)).size} />
          </KpiGrid>
        );
      }}
    >
      {(scope, selected) => {
        const rows = filterByScope(FLEET_AUDIT, scope);
        return (
          <CatalogPanel title="Audit log" hint="Actor, object, and result only. Secret values are never displayed.">
            {rows.length === 0 ? (
              <Empty label="No audit events in the current hierarchy filter." />
            ) : (
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
            )}
          </CatalogPanel>
        );
      }}
    </Shell>
  );
}

export function AdministrationCatalog({ initial }: { initial: CatalogFilters }) {
  const filters = useCatalogFilters(initial);
  return (
    <CatalogBody
      title="Administration"
      subtitle="Console access, roles, and cloud integrations. Secret values are never displayed."
      environment={filters.environment}
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
        <KpiGrid>
          <Kpi label="Users" value={ADMIN_USERS.length} />
          <Kpi label="Integrations" value={ADMIN_INTEGRATIONS.length} />
          <Kpi label="Connected" value={ADMIN_INTEGRATIONS.filter((item) => item.status === "Connected").length} />
          <Kpi label="Production roles" value={1} tone="prd" />
          <Kpi label="Read-only auditors" value={1} />
        </KpiGrid>
      }
    >
      <CatalogPanel title="Users" hint="Role and scope only. Passwords are never displayed.">
        <Table headers={["User", "Role", "Scope", "Last active"]}>
          {ADMIN_USERS.map((user) => (
            <tr key={user.id} className={rowClass(false, user.role === "Platform Admin")}>
              <td className="p-3 font-mono text-xs font-semibold text-ink">{user.user}</td>
              <td className="p-3 text-muted">{user.role}</td>
              <td className="p-3 text-muted">{user.scope}</td>
              <td className="p-3 font-mono text-xs text-muted">{user.lastActive}</td>
            </tr>
          ))}
        </Table>
      </CatalogPanel>
      <CatalogPanel title="Integrations" hint="Connection state only. Client secrets and tokens are never displayed.">
        <Table headers={["Integration", "Status", "Scope", "Note"]}>
          {ADMIN_INTEGRATIONS.map((item) => (
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
    </CatalogBody>
  );
}
