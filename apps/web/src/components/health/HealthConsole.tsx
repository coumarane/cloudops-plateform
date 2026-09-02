"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { CatalogPanel, Kpi, KpiGrid, StatusChip } from "@/components/catalog/CatalogChrome";
import { PageHeader } from "@/components/layout/PageHeader";
import { EnvBadge } from "@/components/status/EnvBadge";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import type { HealthApplication, HealthFilters, HealthIncident, HealthOverview, HealthResource } from "@/lib/health";
import { healthHref } from "@/lib/health";
import type { Environment } from "@/lib/types";

export function HealthConsole({ initial }: { initial: HealthFilters }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const appId = searchParams.get("app") || initial.app;
  const incidentId = searchParams.get("incident") || initial.incident;
  const tab = searchParams.get("tab") || initial.tab || "overview";
  const [statusFilter, setStatusFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [environmentFilter, setEnvironmentFilter] = useState("");
  const [applicationFilter, setApplicationFilter] = useState("");

  const overviewState = useResource((signal) => cloudOpsApi.healthOverview(signal), []);
  const appsState = useResource((signal) => cloudOpsApi.healthApplications(undefined, signal), []);
  const incidentsState = useResource((signal) => cloudOpsApi.healthIncidents(undefined, signal), []);
  const resourcesState = useResource((signal) => cloudOpsApi.healthResources(undefined, signal), []);

  const filtered = useMemo(() => {
    const rows = appsState.status === "success" ? appsState.data.items : [];
    return rows.filter((row) => {
      if (statusFilter && (row.status || "").toLowerCase() !== statusFilter.toLowerCase()) return false;
      if (providerFilter && (row.provider || "").toLowerCase() !== providerFilter.toLowerCase()) return false;
      if (regionFilter && (row.region || "") !== regionFilter) return false;
      if (environmentFilter && (row.environment || "") !== environmentFilter) return false;
      if (applicationFilter && !`${row.name} ${row.applicationId}`.toLowerCase().includes(applicationFilter.toLowerCase())) return false;
      return true;
    });
  }, [appsState, statusFilter, providerFilter, regionFilter, environmentFilter, applicationFilter]);

  function setQuery(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (value) params.set(key, value);
      else params.delete(key);
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  if (incidentId) {
    return <IncidentView incidentId={incidentId} onBack={() => setQuery({ incident: null })} />;
  }
  if (appId) {
    return <ApplicationHealthView applicationId={appId} tab={tab} onBack={() => setQuery({ app: null, tab: null })} onTab={(next) => setQuery({ app: appId, tab: next === "overview" ? null : next })} />;
  }

  return (
    <>
      <PageHeader
        title="Health"
        subtitle="Unified application and Kubernetes health. AWS EKS and Alibaba ACK share the same model. Backend status is the source of truth."
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState state={overviewState} loadingLabel="Loading health overview…" emptyLabel="No health data yet." isEmpty={() => false}>
            {(overview: HealthOverview) => (
              <KpiGrid>
                <Kpi label="Healthy apps" value={overview.healthyApplications} />
                <Kpi label="Degraded apps" value={overview.degradedApplications} tone={overview.degradedApplications ? "warning" : undefined} />
                <Kpi label="Unhealthy apps" value={overview.unhealthyApplications} tone={overview.unhealthyApplications ? "critical" : undefined} />
                <Kpi label="Critical apps" value={overview.criticalApplications} tone={overview.criticalApplications ? "critical" : undefined} />
                <Kpi label="Unhealthy clusters" value={overview.unhealthyClusters} tone={overview.unhealthyClusters ? "critical" : undefined} />
                <Kpi label="Open incidents" value={overview.openIncidents} tone={overview.openIncidents ? "critical" : undefined} />
              </KpiGrid>
            )}
          </QueryState>
          <CatalogPanel title="Applications by health" hint="Status is calculated on the API. The console does not recompute severity.">
            <div className="flex flex-wrap gap-2 border-b border-outline p-3">
              <Filter placeholder="Status" value={statusFilter} onChange={setStatusFilter} />
              <Filter placeholder="Provider" value={providerFilter} onChange={setProviderFilter} />
              <Filter placeholder="Region" value={regionFilter} onChange={setRegionFilter} />
              <Filter placeholder="Environment" value={environmentFilter} onChange={setEnvironmentFilter} />
              <Filter placeholder="Application" value={applicationFilter} onChange={setApplicationFilter} />
            </div>
            <QueryState state={appsState} loadingLabel="Loading applications…" emptyLabel="No application health rows yet." isEmpty={() => filtered.length === 0}>
              {() => (
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                      <th className="p-3">Application</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Summary</th>
                      <th className="p-3">Likely related to</th>
                      <th className="p-3">Provider</th>
                      <th className="p-3">Region</th>
                      <th className="p-3">Environment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((row) => (
                      <tr key={row.id} className="border-b border-outline hover:bg-surface-low">
                        <td className="p-3 font-mono text-xs">
                          <button type="button" className="font-semibold text-action hover:underline" onClick={() => setQuery({ app: row.applicationId })}>
                            {row.name}
                          </button>
                        </td>
                        <td className="p-3">
                          <StatusChip value={row.status} />
                        </td>
                        <td className="p-3 font-mono text-xs text-muted">{row.summary}</td>
                        <td className="p-3 text-xs text-muted">{row.likelyCause || "—"}</td>
                        <td className="p-3 text-muted">{row.provider}</td>
                        <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                        <td className="p-3">{row.environment ? <EnvBadge environment={row.environment as Environment} /> : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </QueryState>
          </CatalogPanel>
          <CatalogPanel title="Open incidents" hint="Incidents open after consecutive failures and resolve after consecutive recoveries. Thresholds are configurable on the API.">
            <QueryState state={incidentsState} loadingLabel="Loading incidents…" emptyLabel="No health incidents." isEmpty={(data) => data.items.filter((item) => item.status !== "RESOLVED").length === 0}>
              {(data) => (
                <IncidentTable incidents={data.items.filter((item) => item.status !== "RESOLVED")} onOpen={(id) => setQuery({ incident: id })} />
              )}
            </QueryState>
          </CatalogPanel>
          <CatalogPanel title="Resources" hint="Normalized Kubernetes and endpoint health. This is operational diagnostics, not a kubectl replacement.">
            <QueryState state={resourcesState} loadingLabel="Loading resources…" emptyLabel="No resource health yet." isEmpty={(data) => data.items.length === 0}>
              {(data) => <ResourceTable resources={data.items.slice(0, 50)} />}
            </QueryState>
          </CatalogPanel>
        </div>
      </main>
    </>
  );
}

function ApplicationHealthView({
  applicationId,
  tab,
  onBack,
  onTab,
}: {
  applicationId: string;
  tab: string;
  onBack: () => void;
  onTab: (tab: string) => void;
}) {
  const state = useResource((signal) => cloudOpsApi.healthApplication(applicationId, signal), [applicationId]);
  const historyState = useResource((signal) => cloudOpsApi.healthApplicationHistory(applicationId, signal), [applicationId]);
  return (
    <>
      <PageHeader title="Application health" subtitle="Workload, pods, ingress, endpoint, certificate, and recent change correlation." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <button type="button" onClick={onBack} className="text-xs font-semibold text-action hover:underline">
            Back to health
          </button>
          <QueryState state={state} loadingLabel="Loading application health…" emptyLabel="Application health not found.">
            {(app: HealthApplication) => (
              <div className="space-y-6">
                <header className="rounded border border-outline bg-white p-4">
                  <p className="font-mono text-xs text-muted">
                    {app.provider} / {app.region} / {app.environment}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-3">
                    <h2 className="text-xl font-semibold text-ink">{app.name}</h2>
                    <StatusChip value={app.status} />
                  </div>
                  <p className="mt-2 text-sm text-muted">{app.summary}</p>
                  {app.likelyCause ? (
                    <p className="mt-3 rounded bg-warning/10 px-3 py-2 text-sm text-warning">
                      Likely related to: {app.likelyCause.replace(/^Likely related to\s+/i, "")}
                    </p>
                  ) : null}
                </header>
                <div className="flex gap-2">
                  {["overview", "timeline"].map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => onTab(item)}
                      className={tab === item || (item === "overview" && !tab) ? "rounded bg-action px-3 py-1 text-xs font-semibold text-white" : "rounded border border-outline px-3 py-1 text-xs"}
                    >
                      {item}
                    </button>
                  ))}
                </div>
                {tab === "timeline" ? (
                  <CatalogPanel title="Health timeline" hint="Deployment, pod, HTTP, and incident events for troubleshooting.">
                    <QueryState state={historyState} loadingLabel="Loading timeline…" emptyLabel="No timeline events." isEmpty={(data) => data.timeline.length === 0}>
                      {(data) => (
                        <ol className="space-y-2 p-4">
                          {data.timeline.map((event) => (
                            <li key={event.id} className="border-l-2 border-outline pl-3 font-mono text-xs text-ink">
                              <span className="text-muted">{event.createdAt}</span>
                              <span className="ml-2 font-semibold">{event.title}</span>
                              {event.detail ? <span className="ml-2 text-muted">{event.detail}</span> : null}
                            </li>
                          ))}
                        </ol>
                      )}
                    </QueryState>
                  </CatalogPanel>
                ) : (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    <SignalCard label="Workload" resource={app.workload} />
                    <SignalCard label="Pods" detail={app.crashloop ? `${app.crashloop} CrashLoopBackOff` : `${app.failedPods} failed`} status={app.crashloop || app.failedPods ? "UNHEALTHY" : "HEALTHY"} />
                    <SignalCard label="Ingress" resource={app.ingress} />
                    <SignalCard label="Endpoint" resource={app.endpoint} />
                    <SignalCard label="Certificate" status={app.certificateStatus || "UNKNOWN"} />
                    <SignalCard
                      label="Latest Deployment"
                      status={app.latestDeployment.status || "UNKNOWN"}
                      detail={app.latestDeployment.commitSha ? `commit ${app.latestDeployment.commitSha.slice(0, 7)}` : app.latestDeployment.startedAt || ""}
                    />
                    <SignalCard
                      label="Latest Pipeline Run"
                      status={app.latestPipelineRun?.status || "UNKNOWN"}
                      detail={app.latestPipelineRun?.externalRunId ? `#${app.latestPipelineRun.externalRunId}` : ""}
                    />
                  </div>
                )}
              </div>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function IncidentView({ incidentId, onBack }: { incidentId: string; onBack: () => void }) {
  const state = useResource((signal) => cloudOpsApi.healthIncident(incidentId, signal), [incidentId]);
  const [message, setMessage] = useState<string | null>(null);
  async function acknowledge() {
    try {
      await cloudOpsApi.acknowledgeIncident(incidentId);
      setMessage("Incident acknowledged.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Acknowledge failed");
    }
  }
  return (
    <>
      <PageHeader title="Health incident" subtitle="Persistent health problems only. Automated checks are not user-audited." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[960px] space-y-4">
          <button type="button" onClick={onBack} className="text-xs font-semibold text-action hover:underline">
            Back to health
          </button>
          <QueryState state={state} loadingLabel="Loading incident…" emptyLabel="Incident not found.">
            {(incident: HealthIncident) => (
              <CatalogPanel title={incident.rootSymptom || incident.id} hint="Acknowledge records a user audit event. Automated checks do not.">
                <dl className="grid grid-cols-2 gap-3 p-4 text-sm">
                  <div>
                    <dt className="text-[10px] font-bold uppercase text-muted">Status</dt>
                    <dd>
                      <StatusChip value={incident.status} />
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[10px] font-bold uppercase text-muted">Severity</dt>
                    <dd>{incident.severity}</dd>
                  </div>
                  <div>
                    <dt className="text-[10px] font-bold uppercase text-muted">Application</dt>
                    <dd>
                      <Link href={healthHref({ app: incident.applicationId })} className="text-action hover:underline">
                        {incident.applicationId}
                      </Link>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[10px] font-bold uppercase text-muted">Scope</dt>
                    <dd className="font-mono text-xs">
                      {incident.provider} / {incident.region} / {incident.environment}
                    </dd>
                  </div>
                </dl>
                {incident.status === "OPEN" ? (
                  <div className="border-t border-outline p-4">
                    <button type="button" onClick={acknowledge} className="rounded border border-outline px-3 py-1.5 text-xs font-semibold text-action">
                      Acknowledge
                    </button>
                    {message ? <p className="mt-2 text-xs text-muted">{message}</p> : null}
                  </div>
                ) : null}
              </CatalogPanel>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function SignalCard({ label, resource, status, detail }: { label: string; resource?: HealthResource | null; status?: string; detail?: string }) {
  const value = status || resource?.status || "UNKNOWN";
  const extra = detail || resource?.summary || "";
  return (
    <article className="rounded border border-outline bg-white p-4">
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <div className="mt-2">
        <StatusChip value={value} />
      </div>
      {extra ? <p className="mt-2 font-mono text-xs text-muted">{extra}</p> : null}
    </article>
  );
}

function IncidentTable({ incidents, onOpen }: { incidents: HealthIncident[]; onOpen: (id: string) => void }) {
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
          <th className="p-3">Incident</th>
          <th className="p-3">Status</th>
          <th className="p-3">Severity</th>
          <th className="p-3">Application</th>
          <th className="p-3">Age</th>
        </tr>
      </thead>
      <tbody>
        {incidents.map((row) => (
          <tr key={row.id} className="border-b border-outline hover:bg-surface-low">
            <td className="p-3">
              <button type="button" className="font-mono text-xs text-action hover:underline" onClick={() => onOpen(row.id)}>
                {row.rootSymptom || row.id}
              </button>
            </td>
            <td className="p-3">
              <StatusChip value={row.status} />
            </td>
            <td className="p-3">{row.severity}</td>
            <td className="p-3 font-mono text-xs">{row.applicationId}</td>
            <td className="p-3 font-mono text-xs text-muted">{row.age}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ResourceTable({ resources }: { resources: HealthResource[] }) {
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
          <th className="p-3">Type</th>
          <th className="p-3">Name</th>
          <th className="p-3">Namespace</th>
          <th className="p-3">Status</th>
          <th className="p-3">Summary</th>
        </tr>
      </thead>
      <tbody>
        {resources.map((row) => (
          <tr key={row.id} className="border-b border-outline">
            <td className="p-3 font-mono text-xs">{row.resourceType}</td>
            <td className="p-3 font-mono text-xs">{row.name}</td>
            <td className="p-3 font-mono text-xs text-muted">{row.namespace || "—"}</td>
            <td className="p-3">
              <StatusChip value={row.status} />
            </td>
            <td className="p-3 font-mono text-xs text-muted">{row.summary}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Filter({ placeholder, value, onChange }: { placeholder: string; value: string; onChange: (value: string) => void }) {
  return (
    <input
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      className="rounded border border-outline px-2 py-1 text-xs"
    />
  );
}
