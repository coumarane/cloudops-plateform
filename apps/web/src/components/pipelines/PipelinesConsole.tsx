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
import {
  formatDuration,
  openInProviderLabel,
  PIPELINE_TABS,
  shortSha,
  type Pipeline,
  type PipelineFilters,
  type PipelineOverview,
  type PipelineRun,
} from "@/lib/pipelines";

export function PipelinesConsole({ initial }: { initial: PipelineFilters }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const runId = searchParams.get("run") || initial.run;
  const pipelineId = searchParams.get("pipeline") || initial.pipeline;
  const tab = searchParams.get("tab") || initial.tab || "overview";
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [branchFilter, setBranchFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [environmentFilter, setEnvironmentFilter] = useState("");
  const [applicationFilter, setApplicationFilter] = useState("");

  const overviewState = useResource((signal) => cloudOpsApi.pipelineOverview(signal), []);
  const pipelinesState = useResource((signal) => cloudOpsApi.pipelineDefinitions(undefined, signal), []);
  const filtered = useMemo(() => {
    const rows = pipelinesState.status === "success" ? pipelinesState.data.items : [];
    return rows.filter((row) => {
      if (statusFilter && (row.latestRun?.status || "").toLowerCase() !== statusFilter.toLowerCase()) return false;
      if (branchFilter && (row.latestRun?.branch || row.defaultBranch) !== branchFilter) return false;
      if (providerFilter && (row.providerKey || "").toLowerCase() !== providerFilter.toLowerCase()) return false;
      if (regionFilter && (row.region || row.latestRun?.region || "") !== regionFilter) return false;
      if (environmentFilter && (row.environment || row.latestRun?.environment || "") !== environmentFilter) return false;
      if (applicationFilter) {
        const haystack = `${row.applicationId || ""} ${row.name}`.toLowerCase();
        if (!haystack.includes(applicationFilter.toLowerCase())) return false;
      }
      return true;
    });
  }, [pipelinesState, statusFilter, branchFilter, providerFilter, regionFilter, environmentFilter, applicationFilter]);

  async function triggerSync() {
    try {
      await cloudOpsApi.triggerPipelineSync();
      setSyncMessage("Pipeline synchronization queued.");
    } catch (error) {
      setSyncMessage(error instanceof Error ? error.message : "Sync failed");
    }
  }

  function setQuery(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (value) params.set(key, value);
      else params.delete(key);
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  if (runId) {
    return <RunView runId={runId} onBack={() => setQuery({ run: null })} />;
  }
  if (pipelineId) {
    return (
      <PipelineView
        pipelineId={pipelineId}
        tab={tab}
        onTab={(next) => setQuery({ pipeline: pipelineId, tab: next === "overview" ? null : next })}
        onOpenRun={(id) => setQuery({ run: id, pipeline: pipelineId })}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="Pipelines"
        subtitle="Provider-neutral DevOps pipelines. GitHub Actions and Azure DevOps share the same model. Provider logs stay on the source system."
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-muted">{syncMessage || "Normalized status is QUEUED, WAITING, RUNNING, SUCCEEDED, FAILED, CANCELLED, SKIPPED, PARTIAL."}</p>
            <button type="button" onClick={triggerSync} className="rounded border border-outline px-3 py-1.5 text-xs font-semibold text-action">
              Sync pipelines
            </button>
          </div>
          <QueryState state={overviewState} loadingLabel="Loading pipeline overview…" emptyLabel="No pipeline data yet." isEmpty={() => false}>
            {(overview: PipelineOverview) => (
              <KpiGrid>
                <Kpi label="Runs today" value={overview.pipelineRunsToday} />
                <Kpi label="Running" value={overview.runningPipelines} />
                <Kpi label="Failed" value={overview.failedPipelines} tone={overview.failedPipelines ? "critical" : undefined} />
                <Kpi label="Failed PRD" value={overview.failedPrdPipelines} tone={overview.failedPrdPipelines ? "prd" : undefined} />
                <Kpi label="Avg duration (s)" value={overview.averageDeploymentDurationSeconds} />
              </KpiGrid>
            )}
          </QueryState>
          <QueryState state={overviewState} loadingLabel="" emptyLabel="No recent pipeline failures." isEmpty={(data) => data.recentFailures.length === 0}>
            {(overview: PipelineOverview) => (
              <CatalogPanel title="Recent pipeline failures" hint="Click a row to open pipeline run details. Full logs stay on the provider.">
                <FailureTable runs={overview.recentFailures} onOpen={(id) => setQuery({ run: id })} />
              </CatalogPanel>
            )}
          </QueryState>
          <CatalogPanel title="Pipeline catalog" hint="Filter by provider, environment, application, status, and branch. Secret values are never displayed.">
            <div className="flex flex-wrap gap-2 border-b border-outline p-3">
              <select className="rounded border border-outline px-2 py-1 text-xs" value={providerFilter} onChange={(event) => setProviderFilter(event.target.value)}>
                <option value="">All providers</option>
                <option value="github-actions">GitHub Actions</option>
                <option value="azure-devops">Azure DevOps</option>
              </select>
              <select className="rounded border border-outline px-2 py-1 text-xs" value={regionFilter} onChange={(event) => setRegionFilter(event.target.value)}>
                <option value="">All regions</option>
                {["AMER", "EMEA", "APAC", "China"].map((region) => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
              </select>
              <select className="rounded border border-outline px-2 py-1 text-xs" value={environmentFilter} onChange={(event) => setEnvironmentFilter(event.target.value)}>
                <option value="">All environments</option>
                {["DEV", "INT/TST", "UAT", "NPD", "PRD"].map((environment) => (
                  <option key={environment} value={environment}>
                    {environment}
                  </option>
                ))}
              </select>
              <input
                className="rounded border border-outline px-2 py-1 text-xs"
                placeholder="Application"
                value={applicationFilter}
                onChange={(event) => setApplicationFilter(event.target.value)}
              />
              <select className="rounded border border-outline px-2 py-1 text-xs" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="">All statuses</option>
                {["QUEUED", "WAITING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "SKIPPED", "PARTIAL"].map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
              <input
                className="rounded border border-outline px-2 py-1 text-xs"
                placeholder="Branch"
                value={branchFilter}
                onChange={(event) => setBranchFilter(event.target.value)}
              />
            </div>
            <QueryState state={pipelinesState} loadingLabel="Loading pipelines…" emptyLabel="No pipelines in the current filter." isEmpty={() => filtered.length === 0}>
              {() => (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-[13px]">
                    <thead>
                      <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                        <th className="p-3">Pipeline</th>
                        <th className="p-3">Provider</th>
                        <th className="p-3">Application</th>
                        <th className="p-3">Repository</th>
                        <th className="p-3">Environment</th>
                        <th className="p-3">Branch</th>
                        <th className="p-3">Latest run</th>
                        <th className="p-3">Duration</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Triggered by</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((row) => (
                        <tr key={row.id} className="border-b border-outline last:border-b-0">
                          <td className="p-3 font-semibold text-ink">
                            <button type="button" className="text-action hover:underline" onClick={() => setQuery({ pipeline: row.id })}>
                              {row.name}
                            </button>
                          </td>
                          <td className="p-3 text-muted">{row.providerName || row.providerKey}</td>
                          <td className="p-3 font-mono text-xs text-muted">{row.applicationId || "—"}</td>
                          <td className="p-3 font-mono text-xs text-muted">
                            {row.repositoryId ? (
                              <Link href={`/github?repo=${row.repositoryId}`} className="hover:underline">
                                {row.repository || row.repositoryId}
                              </Link>
                            ) : (
                              row.repository || "—"
                            )}
                          </td>
                          <td className="p-3">{row.environment ? <EnvBadge environment={row.environment} /> : "—"}</td>
                          <td className="p-3 font-mono text-xs text-muted">{row.latestRun?.branch || row.defaultBranch || "—"}</td>
                          <td className="p-3">
                            {row.latestRun ? (
                              <button type="button" className="text-xs text-action hover:underline" onClick={() => setQuery({ run: row.latestRun!.id })}>
                                {row.latestRun.age || row.latestRun.status}
                              </button>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="p-3 font-mono text-xs text-muted">{formatDuration(row.latestRun?.durationSeconds)}</td>
                          <td className="p-3">
                            <StatusChip value={row.latestRun?.status || "UNKNOWN"} />
                          </td>
                          <td className="p-3 text-xs text-muted">{row.latestRun?.actor || row.latestRun?.trigger || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </QueryState>
          </CatalogPanel>
        </div>
      </main>
    </>
  );
}

function FailureTable({ runs, onOpen }: { runs: PipelineRun[]; onOpen: (id: string) => void }) {
  if (runs.length === 0) {
    return <p className="p-4 text-sm text-muted">No pipeline failures in the current view.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Pipeline</th>
            <th className="p-3">Provider</th>
            <th className="p-3">Environment</th>
            <th className="p-3">Status</th>
            <th className="p-3">Age</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-b border-outline last:border-b-0">
              <td className="p-3">
                <button type="button" className="font-semibold text-action hover:underline" onClick={() => onOpen(run.id)}>
                  {run.pipelineName}
                </button>
              </td>
              <td className="p-3 text-muted">{run.providerName || run.providerKey}</td>
              <td className="p-3">
                {run.environment ? <EnvBadge environment={run.environment} /> : "—"}
                <span className="ml-1 text-[10px] text-muted">
                  {run.provider} {run.region}
                </span>
              </td>
              <td className="p-3">
                <StatusChip value={run.status} />
              </td>
              <td className="p-3 font-mono text-xs text-muted">{run.age}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PipelineView({
  pipelineId,
  tab,
  onTab,
  onOpenRun,
}: {
  pipelineId: string;
  tab: string;
  onTab: (tab: string) => void;
  onOpenRun: (id: string) => void;
}) {
  const pipeline = useResource((signal) => cloudOpsApi.pipelineDefinition(pipelineId, signal), [pipelineId]);
  const runs = useResource((signal) => cloudOpsApi.pipelineRunsFor(pipelineId, signal), [pipelineId]);
  return (
    <>
      <PageHeader title="Pipeline" subtitle="Normalized pipeline details, runs, and environment mappings." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState state={pipeline} loadingLabel="Loading pipeline…" emptyLabel="Pipeline not found." isEmpty={() => false}>
            {(row: Pipeline) => (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">{row.name}</h2>
                    <p className="font-mono text-xs text-muted">
                      {row.providerName} · {row.repository || "no repository"} · {row.defaultBranch || "—"}
                    </p>
                  </div>
                  {row.htmlUrl ? (
                    <a href={row.htmlUrl} className="rounded border border-outline px-3 py-1.5 text-xs font-semibold text-action" target="_blank" rel="noreferrer">
                      {openInProviderLabel(row.providerKey)}
                    </a>
                  ) : null}
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Meta label="Application" value={row.applicationId || "—"} />
                  <Meta label="Latest run" value={row.latestRun?.status || "—"} />
                  <Meta label="Success rate" value={row.successRate != null ? `${row.successRate}%` : "—"} />
                  <Meta label="Average duration" value={formatDuration(row.averageDurationSeconds)} />
                </div>
                <div className="flex gap-2">
                  {PIPELINE_TABS.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => onTab(item)}
                      className={`rounded border px-3 py-1 text-xs font-semibold capitalize ${tab === item ? "border-action text-action" : "border-outline text-muted"}`}
                    >
                      {item === "environments" ? "Environment Mapping" : item}
                    </button>
                  ))}
                </div>
                {tab === "runs" ? (
                  <CatalogPanel title="Runs" hint="Normalized pipeline runs. Provider-native status is preserved separately.">
                    <RunTable runs={runs.status === "success" ? runs.data.items : []} onOpen={onOpenRun} />
                  </CatalogPanel>
                ) : null}
                {tab === "environments" ? (
                  <CatalogPanel title="Environment mapping" hint="Explicit Pipeline → CloudOps environment mappings. Names are not matched automatically.">
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-left text-[13px]">
                        <thead>
                          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                            <th className="p-3">Branch pattern</th>
                            <th className="p-3">Stage</th>
                            <th className="p-3">CloudOps environment</th>
                            <th className="p-3">Priority</th>
                          </tr>
                        </thead>
                        <tbody>
                          {row.mappedEnvironments.map((mapping) => (
                            <tr key={mapping.id} className="border-b border-outline last:border-b-0">
                              <td className="p-3 font-mono text-xs">{mapping.branchPattern}</td>
                              <td className="p-3 text-muted">{mapping.stageName || "—"}</td>
                              <td className="p-3">
                                {mapping.environment ? `${mapping.provider} / ${mapping.region} / ${mapping.environment}` : mapping.environmentId}
                              </td>
                              <td className="p-3 font-mono text-xs">{mapping.priority}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CatalogPanel>
                ) : null}
                {tab === "configuration" ? (
                  <CatalogPanel title="Configuration" hint="Provider metadata only. Authentication material stays in the secret backend.">
                    <dl className="grid grid-cols-2 gap-3 p-4 text-sm">
                      <div>
                        <dt className="text-[11px] uppercase text-muted">Provider</dt>
                        <dd>{row.providerName}</dd>
                      </div>
                      <div>
                        <dt className="text-[11px] uppercase text-muted">External ID</dt>
                        <dd className="font-mono text-xs">{row.id}</dd>
                      </div>
                      <div>
                        <dt className="text-[11px] uppercase text-muted">Enabled</dt>
                        <dd>{row.enabled ? "Yes" : "No"}</dd>
                      </div>
                      <div>
                        <dt className="text-[11px] uppercase text-muted">Default branch</dt>
                        <dd className="font-mono text-xs">{row.defaultBranch || "—"}</dd>
                      </div>
                    </dl>
                  </CatalogPanel>
                ) : null}
                {tab === "overview" ? (
                  <CatalogPanel title="Latest run" hint="Pipeline → run → deployment correlation uses stable IDs.">
                    {row.latestRun ? (
                      <button type="button" className="p-4 text-left text-sm text-action hover:underline" onClick={() => onOpenRun(row.latestRun!.id)}>
                        {row.latestRun.status} · {row.latestRun.branch} · {shortSha(row.latestRun.commitSha)} · {row.latestRun.age}
                      </button>
                    ) : (
                      <p className="p-4 text-sm text-muted">No runs synchronized yet.</p>
                    )}
                  </CatalogPanel>
                ) : null}
              </>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function RunTable({ runs, onOpen }: { runs: PipelineRun[]; onOpen: (id: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Run</th>
            <th className="p-3">Branch</th>
            <th className="p-3">Commit</th>
            <th className="p-3">Environment</th>
            <th className="p-3">Actor</th>
            <th className="p-3">Started</th>
            <th className="p-3">Duration</th>
            <th className="p-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-b border-outline last:border-b-0">
              <td className="p-3">
                <button type="button" className="font-mono text-xs text-action hover:underline" onClick={() => onOpen(run.id)}>
                  {run.externalRunId || run.id}
                </button>
              </td>
              <td className="p-3 font-mono text-xs">{run.branch || "—"}</td>
              <td className="p-3 font-mono text-xs">{shortSha(run.commitSha)}</td>
              <td className="p-3">{run.environment ? <EnvBadge environment={run.environment} /> : "—"}</td>
              <td className="p-3 text-xs text-muted">{run.actor || run.trigger || "—"}</td>
              <td className="p-3 font-mono text-xs text-muted">{run.age}</td>
              <td className="p-3 font-mono text-xs">{formatDuration(run.durationSeconds)}</td>
              <td className="p-3">
                <StatusChip value={run.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RunView({ runId, onBack }: { runId: string; onBack: () => void }) {
  const state = useResource((signal) => cloudOpsApi.pipelineRun(runId, signal), [runId]);
  return (
    <>
      <PageHeader title="Pipeline run" subtitle="Run → stages → jobs. Full provider logs are not stored in CloudOps." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <button type="button" onClick={onBack} className="text-xs font-semibold text-action hover:underline">
            Back to pipelines
          </button>
          <QueryState state={state} loadingLabel="Loading pipeline run…" emptyLabel="Pipeline run not found." isEmpty={() => false}>
            {(run: PipelineRun) => (
              <>
                <div className="flex justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">{run.pipelineName}</h2>
                    <p className="font-mono text-xs text-muted">
                      {run.repository} · {run.branch} · {shortSha(run.commitSha)} · {run.actor} · {run.trigger}
                    </p>
                  </div>
                  {run.externalUrl ? (
                    <a href={run.externalUrl} className="rounded border border-outline px-3 py-1.5 text-xs font-semibold text-action" target="_blank" rel="noreferrer">
                      {openInProviderLabel(run.providerKey)} logs
                    </a>
                  ) : null}
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Meta label="Status" value={run.status} />
                  <Meta label="Run ID" value={run.externalRunId || run.id} />
                  <Meta label="Actor" value={run.actor || "—"} />
                  <Meta label="Trigger" value={run.trigger || "—"} />
                  <Meta label="Repository" value={run.repository || "—"} />
                  <Meta label="Branch" value={run.branch || "—"} />
                  <Meta label="Commit" value={shortSha(run.commitSha)} />
                  <Meta label="CloudOps environment" value={run.provider ? `${run.provider} / ${run.region} / ${run.environment}` : "Unmapped"} />
                  <Meta label="Application" value={run.applicationId || "—"} />
                  <Meta label="Deployment" value={run.deploymentId || "—"} />
                  <Meta label="Cluster" value={run.clusterId || "—"} />
                  <Meta label="Started" value={run.startedAt || "—"} />
                  <Meta label="Finished" value={run.completedAt || "—"} />
                  <Meta label="Duration" value={formatDuration(run.durationSeconds)} />
                </div>
                <CatalogPanel title="Timeline" hint="Pipeline run → stages → jobs. Step logs remain on the provider.">
                  <ol className="space-y-3 p-4">
                    {(run.stages || []).length === 0 && (run.jobs || []).length === 0 ? (
                      <li className="text-sm text-muted">No stages or jobs synchronized for this run yet.</li>
                    ) : null}
                    {(run.stages || []).map((stage) => (
                      <li key={stage.id} className="rounded border border-outline p-3">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-semibold text-ink">Stage: {stage.name}</p>
                          <StatusChip value={stage.status} />
                        </div>
                        <ul className="mt-2 space-y-2">
                          {(run.jobs || [])
                            .filter((job) => !job.stageId || job.stageId === stage.id)
                            .map((job) => (
                              <li key={job.id} className="rounded bg-canvas p-2">
                                <div className="flex items-center justify-between">
                                  <p className="font-mono text-xs font-semibold">{job.name}</p>
                                  <StatusChip value={job.status} />
                                </div>
                                <p className="mt-1 text-[11px] text-muted">
                                  {formatDuration(job.durationSeconds)}
                                  {job.htmlUrl ? (
                                    <>
                                      {" · "}
                                      <a href={job.htmlUrl} className="text-action hover:underline" target="_blank" rel="noreferrer">
                                        Provider logs
                                      </a>
                                    </>
                                  ) : null}
                                </p>
                              </li>
                            ))}
                        </ul>
                      </li>
                    ))}
                    {(run.stages || []).length === 0
                      ? (run.jobs || []).map((job) => (
                          <li key={job.id} className="rounded border border-outline p-3">
                            <div className="flex items-center justify-between">
                              <p className="font-mono text-xs font-semibold">{job.name}</p>
                              <StatusChip value={job.status} />
                            </div>
                          </li>
                        ))
                      : null}
                  </ol>
                </CatalogPanel>
              </>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-outline bg-white p-3">
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-mono text-xs text-ink">{value}</p>
    </div>
  );
}
