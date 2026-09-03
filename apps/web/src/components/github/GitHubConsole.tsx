"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { CatalogPanel, Kpi, KpiGrid, StatusChip } from "@/components/catalog/CatalogChrome";
import { PageHeader } from "@/components/layout/PageHeader";
import { EnvBadge } from "@/components/status/EnvBadge";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import { isProductionEnvironment } from "@/lib/dashboard";
import {
  formatDuration,
  GITHUB_REPO_TABS,
  GITHUB_SECRET_MASK,
  githubHref,
  shortSha,
  type GithubFilters,
  type GithubRepository,
  type GithubSecret,
  type GithubVariable,
  type GithubWorkflowRun,
} from "@/lib/github";
import { emptyGithubOverview } from "@/lib/github-data";

export function GitHubConsole({ initial }: { initial: GithubFilters }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const runId = searchParams.get("run") || initial.run;
  const workflowId = searchParams.get("workflow") || initial.workflow;
  const repoId = searchParams.get("repo") || initial.repo;
  const tab = searchParams.get("tab") || initial.tab || "overview";
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const overviewState = useResource((signal) => cloudOpsApi.scmOverview(signal), []);
  const reposState = useResource((signal) => cloudOpsApi.scmRepositories(signal), []);

  async function triggerSync() {
    try {
      await cloudOpsApi.triggerGithubSync();
      setSyncMessage("GitHub synchronization queued.");
    } catch (error) {
      setSyncMessage(error instanceof Error ? error.message : "Sync failed");
    }
  }

  function setQuery(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (!value) params.delete(key);
      else params.set(key, value);
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  if (runId) {
    return <RunView runId={runId} onBack={() => setQuery({ run: null })} />;
  }
  if (workflowId) {
    return <WorkflowView workflowId={workflowId} onOpenRun={(id) => setQuery({ run: id })} />;
  }
  if (repoId) {
    return (
      <RepositoryView
        repositoryId={repoId}
        tab={tab}
        onTab={(next) => setQuery({ tab: next === "overview" ? null : next })}
        onOpenWorkflow={(id) => setQuery({ workflow: id, repo: repoId })}
        onOpenRun={(id) => setQuery({ run: id })}
      />
    );
  }

  const overview = overviewState.status === "success" ? overviewState.data : emptyGithubOverview();
  const repos = reposState.status === "success" ? reposState.data.items : [];

  return (
    <>
      <PageHeader
        title="GitHub"
        subtitle="Organizations, repositories, Actions workflows, variables, and secret metadata. Secret values are never displayed."
        meta={overview.lastSynced ? `Last synced: ${overview.lastSynced}` : "Last synced: —"}
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted">GitHub App integration. Tokens and private keys stay in the secret backend.</p>
            <button type="button" onClick={triggerSync} className="rounded border border-outline px-3 py-1.5 text-xs font-semibold text-action">
              Sync GitHub
            </button>
          </div>
          {syncMessage ? <p className="text-sm text-muted">{syncMessage}</p> : null}
          <KpiGrid>
            <Kpi label="Repositories" value={overview.repositories} />
            <Kpi label="Active workflows" value={overview.activeWorkflows} />
            <Kpi label="Running" value={overview.runningWorkflows} />
            <Kpi label="Failed" value={overview.failedWorkflows} tone={overview.failedWorkflows ? "critical" : undefined} />
            <Kpi label="Failed last 24h" value={overview.failedWorkflowsLast24h} tone={overview.failedWorkflowsLast24h ? "critical" : undefined} />
            <Kpi label="Unmapped repos" value={overview.unmappedRepositories} tone={overview.unmappedRepositories ? "warning" : undefined} />
            <Kpi label="Unmapped GitHub envs" value={overview.unmappedGithubEnvironments} tone={overview.unmappedGithubEnvironments ? "warning" : undefined} />
          </KpiGrid>
          <QueryState state={overviewState} loadingLabel="Loading GitHub overview…" emptyLabel="No GitHub data yet. Add a GitHub App under Administration → Integrations." isEmpty={() => false}>
            {() => (
              <CatalogPanel title="Recent workflow failures" hint="Failed GitHub Actions runs. Full logs stay on GitHub.">
                <RunTable runs={(overview.recentFailures || []).filter(Boolean) as GithubWorkflowRun[]} onOpen={(id) => setQuery({ run: id })} />
              </CatalogPanel>
            )}
          </QueryState>
          <CatalogPanel title="Repositories" hint="Open a repository for applications, environments, workflows, variables, and secrets.">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-[13px]">
                <thead>
                  <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                    <th className="p-3">Repository</th>
                    <th className="p-3">Visibility</th>
                    <th className="p-3">Default branch</th>
                    <th className="p-3">Applications</th>
                    <th className="p-3">GitHub</th>
                  </tr>
                </thead>
                <tbody>
                  {repos.map((repo) => (
                    <tr key={repo.id} className="border-b border-outline last:border-b-0">
                      <td className="p-3 font-mono text-xs font-semibold text-ink">
                        <Link href={githubHref({ repo: repo.id })} className="hover:underline">
                          {repo.fullName}
                        </Link>
                      </td>
                      <td className="p-3 text-muted">{repo.visibility}</td>
                      <td className="p-3 font-mono text-xs text-muted">{repo.defaultBranch}</td>
                      <td className="p-3 font-mono text-xs text-muted">{repo.applicationIds.length}</td>
                      <td className="p-3">
                        {repo.htmlUrl ? (
                          <a href={repo.htmlUrl} className="text-xs font-semibold text-action hover:underline" target="_blank" rel="noreferrer">
                            Open in GitHub
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CatalogPanel>
          <VariablesSecretsPanel />
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Secret values are never displayed in this console.
          </p>
        </div>
      </main>
    </>
  );
}

function RunTable({ runs, onOpen }: { runs: GithubWorkflowRun[]; onOpen: (id: string) => void }) {
  if (runs.length === 0) {
    return <p className="p-4 text-sm text-muted">No workflow failures in the current view.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Run</th>
            <th className="p-3">Repository</th>
            <th className="p-3">Environment</th>
            <th className="p-3">Actor</th>
            <th className="p-3">Started</th>
            <th className="p-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-b border-outline last:border-b-0">
              <td className="p-3 font-mono text-xs">
                <button type="button" className="font-semibold text-action hover:underline" onClick={() => onOpen(run.id)}>
                  {run.workflow || run.id}
                </button>
              </td>
              <td className="p-3 font-mono text-xs text-muted">{run.repository}</td>
              <td className="p-3">{run.environment ? <EnvBadge environment={run.environment} /> : run.githubEnvironment || "—"}</td>
              <td className="p-3 text-muted">{run.actor}</td>
              <td className="p-3 font-mono text-xs text-muted">{run.age || "—"}</td>
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

function RepositoryView({
  repositoryId,
  tab,
  onTab,
  onOpenWorkflow,
  onOpenRun,
}: {
  repositoryId: string;
  tab: string;
  onTab: (tab: string) => void;
  onOpenWorkflow: (id: string) => void;
  onOpenRun: (id: string) => void;
}) {
  const state = useResource((signal) => cloudOpsApi.scmRepository(repositoryId, signal), [repositoryId]);
  const workflows = useResource((signal) => cloudOpsApi.scmRepositoryWorkflows(repositoryId, signal), [repositoryId]);
  return (
    <>
      <PageHeader title="Repository" subtitle="GitHub repository mapped to CloudOps applications and environments." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState state={state} loadingLabel="Loading repository…" emptyLabel="Repository not found." isEmpty={() => false}>
            {(repo: GithubRepository) => (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-mono text-lg font-semibold text-ink">{repo.fullName}</h2>
                    <p className="text-sm text-muted">{repo.description || "No description."}</p>
                  </div>
                  {repo.htmlUrl ? (
                    <a href={repo.htmlUrl} className="rounded border border-outline px-3 py-1.5 text-xs font-semibold text-action" target="_blank" rel="noreferrer">
                      Open in GitHub
                    </a>
                  ) : null}
                </div>
                <nav className="flex flex-wrap gap-2">
                  {GITHUB_REPO_TABS.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => onTab(item)}
                      className={item === tab ? "rounded bg-action px-3 py-1 text-xs font-semibold text-white" : "rounded border border-outline px-3 py-1 text-xs font-semibold text-muted"}
                    >
                      {item}
                    </button>
                  ))}
                </nav>
                {tab === "applications" ? (
                  <CatalogPanel title="Applications" hint="Many-to-many repository to application association.">
                    <p className="p-4 font-mono text-xs text-muted">
                      {repo.applicationIds.length ? repo.applicationIds.join(", ") : "No CloudOps applications are linked yet."}
                    </p>
                  </CatalogPanel>
                ) : null}
                {tab === "environments" ? (
                  <CatalogPanel title="GitHub environments" hint="Explicit mapping to CloudOps environments. Names may differ.">
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-left text-[13px]">
                        <thead>
                          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                            <th className="p-3">GitHub environment</th>
                            <th className="p-3">CloudOps</th>
                            <th className="p-3">Active</th>
                          </tr>
                        </thead>
                        <tbody>
                          {repo.environments.map((item) => (
                            <tr key={item.id} className="border-b border-outline last:border-b-0">
                              <td className="p-3 font-mono text-xs">{item.githubEnvironment}</td>
                              <td className="p-3 text-muted">
                                {item.provider ? `${item.provider} / ${item.region} / ${item.environment}` : "Unmapped"}
                              </td>
                              <td className="p-3">{item.active ? "Yes" : "No"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CatalogPanel>
                ) : null}
                {tab === "workflows" || tab === "overview" ? (
                  <CatalogPanel title="Workflows" hint="GitHub Actions workflow metadata. YAML is not stored in CloudOps.">
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse text-left text-[13px]">
                        <thead>
                          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                            <th className="p-3">Workflow</th>
                            <th className="p-3">Path</th>
                            <th className="p-3">State</th>
                            <th className="p-3">Latest</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(workflows.status === "success" ? workflows.data.items : []).map((workflow) => (
                            <tr key={workflow.id} className="border-b border-outline last:border-b-0">
                              <td className="p-3 font-mono text-xs">
                                <button type="button" className="font-semibold text-action hover:underline" onClick={() => onOpenWorkflow(workflow.id)}>
                                  {workflow.name}
                                </button>
                              </td>
                              <td className="p-3 font-mono text-xs text-muted">{workflow.path}</td>
                              <td className="p-3">{workflow.state}</td>
                              <td className="p-3">
                                {workflow.latestRun ? (
                                  <button type="button" className="text-xs text-action hover:underline" onClick={() => onOpenRun(workflow.latestRun!.id)}>
                                    {workflow.latestRun.status}
                                  </button>
                                ) : (
                                  "—"
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CatalogPanel>
                ) : null}
                {tab === "variables" || tab === "secrets" ? <VariablesSecretsPanel repositoryId={repositoryId} initialTab={tab} /> : null}
              </>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function WorkflowView({ workflowId, onOpenRun }: { workflowId: string; onOpenRun: (id: string) => void }) {
  const workflow = useResource((signal) => cloudOpsApi.scmWorkflow(workflowId, signal), [workflowId]);
  const runs = useResource((signal) => cloudOpsApi.scmWorkflowRuns(workflowId, signal), [workflowId]);
  return (
    <>
      <PageHeader title="Workflow" subtitle="GitHub Actions workflow and recent runs." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState state={workflow} loadingLabel="Loading workflow…" emptyLabel="Workflow not found." isEmpty={() => false}>
            {(item) => (
              <>
                <div className="flex justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">{item.name}</h2>
                    <p className="font-mono text-xs text-muted">{item.path}</p>
                  </div>
                  {item.htmlUrl ? (
                    <a href={item.htmlUrl} className="text-xs font-semibold text-action hover:underline" target="_blank" rel="noreferrer">
                      Open in GitHub
                    </a>
                  ) : null}
                </div>
                <KpiGrid>
                  <Kpi label="Success rate" value={Math.round(item.successRate ?? 0)} />
                  <Kpi label="Avg duration (s)" value={item.averageDurationSeconds ?? 0} />
                </KpiGrid>
                <CatalogPanel title="Recent runs" hint="Run, branch, commit, environment, actor, started, duration, status.">
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
                        {(runs.status === "success" ? runs.data.items : []).map((run) => (
                          <tr key={run.id} className="border-b border-outline last:border-b-0">
                            <td className="p-3">
                              <button type="button" className="font-mono text-xs text-action hover:underline" onClick={() => onOpenRun(run.id)}>
                                {run.id}
                              </button>
                            </td>
                            <td className="p-3 font-mono text-xs">{run.branch}</td>
                            <td className="p-3 font-mono text-xs">{shortSha(run.commitSha)}</td>
                            <td className="p-3">{run.environment ? <EnvBadge environment={run.environment} /> : run.githubEnvironment || "—"}</td>
                            <td className="p-3 text-muted">{run.actor}</td>
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
                </CatalogPanel>
              </>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function RunView({ runId, onBack }: { runId: string; onBack: () => void }) {
  const state = useResource((signal) => cloudOpsApi.scmRun(runId, signal), [runId]);
  return (
    <>
      <PageHeader title="Workflow run" subtitle="Jobs timeline and CloudOps correlation. Full logs stay on GitHub." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <button type="button" onClick={onBack} className="text-xs font-semibold text-action hover:underline">
            Back to GitHub
          </button>
          <QueryState state={state} loadingLabel="Loading workflow run…" emptyLabel="Workflow run not found." isEmpty={() => false}>
            {(run: GithubWorkflowRun) => (
              <>
                <div className="flex justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">{run.workflow}</h2>
                    <p className="font-mono text-xs text-muted">
                      {run.repository} · {run.branch} · {shortSha(run.commitSha)} · {run.actor} · {run.event}
                    </p>
                  </div>
                  {run.htmlUrl ? (
                    <a href={run.htmlUrl} className="rounded border border-outline px-3 py-1.5 text-xs font-semibold text-action" target="_blank" rel="noreferrer">
                      View logs on GitHub
                    </a>
                  ) : null}
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Meta label="Status" value={run.status} />
                  <Meta label="CloudOps environment" value={run.provider ? `${run.provider} / ${run.region} / ${run.environment}` : "Unmapped"} />
                  <Meta label="Application" value={run.applicationId || "—"} />
                  <Meta label="Deployment" value={run.deploymentId || "—"} />
                </div>
                <CatalogPanel title="Jobs" hint="Workflow run → jobs. Step logs are not duplicated in CloudOps.">
                  <ol className="space-y-2 p-4">
                    {(run.jobs || []).map((job) => (
                      <li key={job.id} className="rounded border border-outline p-3">
                        <div className="flex items-center justify-between">
                          <p className="font-mono text-xs font-semibold text-ink">{job.name}</p>
                          <StatusChip value={job.status} />
                        </div>
                        <p className="mt-1 text-xs text-muted">
                          {formatDuration(job.durationSeconds)} · {job.runnerName || "runner unknown"}
                          {job.htmlUrl ? (
                            <>
                              {" · "}
                              <a href={job.htmlUrl} className="text-action hover:underline" target="_blank" rel="noreferrer">
                                GitHub logs
                              </a>
                            </>
                          ) : null}
                        </p>
                      </li>
                    ))}
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
    <article className="rounded border border-outline bg-white p-3">
      <p className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-mono text-xs text-ink">{value}</p>
    </article>
  );
}

function VariablesSecretsPanel({ repositoryId, initialTab = "variables" }: { repositoryId?: string; initialTab?: string }) {
  const [tab, setTab] = useState(initialTab === "secrets" ? "secrets" : "variables");
  const [organization, setOrganization] = useState("");
  const [scope, setScope] = useState("");
  const query: Record<string, string> = {};
  if (repositoryId) query.repository_id = repositoryId;
  if (organization) query.organization = organization;
  if (scope) query.scope = scope;
  const variables = useResource((signal) => cloudOpsApi.scmVariables(query, signal), [repositoryId, organization, scope]);
  const secrets = useResource((signal) => cloudOpsApi.scmSecrets(query, signal), [repositoryId, organization, scope]);
  const [dialog, setDialog] = useState<GithubSecret | "create" | null>(null);

  return (
    <CatalogPanel title="Variables & secrets" hint="Secret values cannot be retrieved from GitHub. CloudOps never displays plaintext secrets.">
      <div className="flex flex-wrap gap-2 border-b border-outline p-3">
        <button type="button" className={tab === "variables" ? "text-xs font-semibold text-action" : "text-xs text-muted"} onClick={() => setTab("variables")}>
          Variables
        </button>
        <button type="button" className={tab === "secrets" ? "text-xs font-semibold text-action" : "text-xs text-muted"} onClick={() => setTab("secrets")}>
          Secrets
        </button>
        <input
          className="ml-auto rounded border border-outline px-2 py-1 text-xs"
          placeholder="Organization"
          value={organization}
          onChange={(event) => setOrganization(event.target.value)}
        />
        <input className="rounded border border-outline px-2 py-1 text-xs" placeholder="Scope" value={scope} onChange={(event) => setScope(event.target.value)} />
      </div>
      {tab === "variables" ? (
        <VariableTable rows={variables.status === "success" ? variables.data.items : []} />
      ) : (
        <SecretTable
          rows={secrets.status === "success" ? secrets.data.items : []}
          onReplace={(row) => setDialog(row)}
          onCreate={() => setDialog("create")}
        />
      )}
      {dialog ? <SecretDialog secret={dialog === "create" ? null : dialog} repositoryId={repositoryId} onClose={() => setDialog(null)} /> : null}
    </CatalogPanel>
  );
}

function VariableTable({ rows }: { rows: GithubVariable[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Name</th>
            <th className="p-3">Scope</th>
            <th className="p-3">Repository</th>
            <th className="p-3">Environment</th>
            <th className="p-3">Value</th>
            <th className="p-3">Updated</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-outline last:border-b-0">
              <td className="p-3 font-mono text-xs">{row.name}</td>
              <td className="p-3 text-muted">{row.scope}</td>
              <td className="p-3 font-mono text-xs text-muted">{row.repository}</td>
              <td className="p-3">{row.environment ? <EnvBadge environment={row.environment} /> : row.githubEnvironment || "—"}</td>
              <td className="p-3 font-mono text-xs">{row.sensitive ? GITHUB_SECRET_MASK : row.value}</td>
              <td className="p-3 font-mono text-xs text-muted">{row.updatedAt || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SecretTable({
  rows,
  onReplace,
  onCreate,
}: {
  rows: GithubSecret[];
  onReplace: (row: GithubSecret) => void;
  onCreate: () => void;
}) {
  return (
    <div>
      <div className="flex justify-end p-3">
        <button type="button" onClick={onCreate} className="text-xs font-semibold text-action hover:underline">
          Create secret
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-[13px]">
          <thead>
            <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
              <th className="p-3">Name</th>
              <th className="p-3">Scope</th>
              <th className="p-3">Repository</th>
              <th className="p-3">Environment</th>
              <th className="p-3">Value</th>
              <th className="p-3">Updated</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-outline last:border-b-0">
                <td className="p-3 font-mono text-xs">{row.name}</td>
                <td className="p-3 text-muted">{row.scope}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.repository}</td>
                <td className="p-3">{row.environment ? <EnvBadge environment={row.environment} /> : row.githubEnvironment || "—"}</td>
                <td className="p-3 font-mono text-xs">{GITHUB_SECRET_MASK}</td>
                <td className="p-3 font-mono text-xs text-muted">{row.updatedAt || "—"}</td>
                <td className="p-3 space-x-2">
                  <button type="button" className="text-xs font-semibold text-action hover:underline" onClick={() => onReplace(row)}>
                    Replace
                  </button>
                  <span className="text-xs text-muted">No view or download</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SecretDialog({
  secret,
  repositoryId,
  onClose,
}: {
  secret: GithubSecret | null;
  repositoryId?: string;
  onClose: () => void;
}) {
  const production = secret?.environment ? isProductionEnvironment(secret.environment) : false;
  const [name, setName] = useState(secret?.name || "");
  const [value, setValue] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [reason, setReason] = useState("");
  const [ticket, setTicket] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const body = {
        repositoryId: secret?.repositoryId || repositoryId,
        name,
        value,
        githubEnvironment: secret?.githubEnvironment || "",
        confirmed,
        reason,
        changeTicket: ticket,
      };
      if (secret) {
        await cloudOpsApi.replaceGithubSecret(secret.id, body);
      } else {
        await cloudOpsApi.createGithubSecret(body);
      }
      setValue("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "GitHub secret update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-t border-outline p-4">
      <h3 className="text-sm font-semibold text-ink">{secret ? "Replace GitHub secret" : "Create GitHub secret"}</h3>
      <p className="mt-1 text-xs text-muted">The new value is sent to GitHub over TLS and is never stored in PostgreSQL, logs, or audit records.</p>
      {production ? (
        <p className="mt-2 text-xs font-semibold text-prd">Production GitHub secret. Confirmation, reason, and github_secret:prod_update are required.</p>
      ) : null}
      {!secret ? (
        <input className="mt-2 w-full rounded border border-outline px-2 py-1 text-xs" placeholder="Secret name" value={name} onChange={(event) => setName(event.target.value)} />
      ) : (
        <p className="mt-2 font-mono text-xs">{secret.name}</p>
      )}
      <input
        className="mt-2 w-full rounded border border-outline px-2 py-1 text-xs"
        placeholder="New secret value"
        type="password"
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      {production ? (
        <>
          <label className="mt-2 flex items-center gap-2 text-xs">
            <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
            I confirm this production GitHub secret change
          </label>
          <input className="mt-2 w-full rounded border border-outline px-2 py-1 text-xs" placeholder="Reason" value={reason} onChange={(event) => setReason(event.target.value)} />
          <input className="mt-2 w-full rounded border border-outline px-2 py-1 text-xs" placeholder="Change ticket (optional)" value={ticket} onChange={(event) => setTicket(event.target.value)} />
        </>
      ) : null}
      {error ? <p className="mt-2 text-xs text-critical">{error}</p> : null}
      <div className="mt-3 flex gap-2">
        <button type="button" disabled={busy} onClick={submit} className="rounded bg-action px-3 py-1 text-xs font-semibold text-white">
          {secret ? "Replace" : "Create"}
        </button>
        <button type="button" onClick={onClose} className="text-xs text-muted">
          Cancel
        </button>
      </div>
    </div>
  );
}
