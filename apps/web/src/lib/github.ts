import type { Environment, Provider, Region } from "@/lib/types";

export type GithubOverview = {
  repositories: number;
  activeWorkflows: number;
  runningWorkflows: number;
  failedWorkflows: number;
  failedWorkflowsLast24h: number;
  succeededWorkflows: number;
  unmappedRepositories: number;
  unmappedGithubEnvironments: number;
  recentFailures: GithubWorkflowRun[];
  lastSynced?: string;
};

export type GithubOrganization = {
  id: string;
  login: string;
  name: string;
  avatarUrl: string;
  htmlUrl: string;
  status: string;
  lastSynchronizedAt?: string | null;
};

export type GithubRepository = {
  id: string;
  organization: string;
  name: string;
  fullName: string;
  description: string;
  defaultBranch: string;
  visibility: string;
  archived: boolean;
  htmlUrl: string;
  pushedAt?: string | null;
  lastSynchronizedAt?: string | null;
  applicationIds: string[];
  environments: Array<{
    id: string;
    githubEnvironment: string;
    active: boolean;
    cloudopsEnvironmentId: string;
    provider?: Provider | null;
    region?: Region | null;
    environment?: Environment | null;
  }>;
  unmappedEnvironments: number;
};

export type GithubWorkflow = {
  id: string;
  repositoryId: string;
  name: string;
  path: string;
  state: string;
  htmlUrl: string;
  latestRun?: GithubWorkflowRun | null;
  successRate?: number | null;
  averageDurationSeconds?: number | null;
};

export type GithubWorkflowRun = {
  id: string;
  workflowId: string;
  repositoryId: string;
  repository: string;
  workflow: string;
  workflowPath: string;
  branch: string;
  commitSha: string;
  event: string;
  actor: string;
  status: string;
  githubStatus: string;
  githubConclusion: string;
  startedAt?: string | null;
  completedAt?: string | null;
  durationSeconds?: number | null;
  htmlUrl: string;
  githubEnvironment: string;
  applicationId: string;
  deploymentId: string;
  clusterId: string;
  provider?: Provider | null;
  region?: Region | null;
  environment?: Environment | null;
  age?: string;
  jobs?: GithubWorkflowJob[];
};

export type GithubWorkflowJob = {
  id: string;
  runId: string;
  name: string;
  status: string;
  startedAt?: string | null;
  completedAt?: string | null;
  durationSeconds?: number | null;
  runnerName: string;
  runnerType: string;
  htmlUrl: string;
};

export type GithubVariable = {
  id: string;
  name: string;
  scope: string;
  repositoryId: string;
  repository: string;
  organization: string;
  githubEnvironment: string;
  value: string;
  sensitive: boolean;
  updatedAt?: string | null;
  environment?: Environment | null;
};

export type GithubSecret = {
  id: string;
  name: string;
  scope: string;
  repositoryId: string;
  repository: string;
  organization: string;
  githubEnvironment: string;
  value: string;
  updatedAt?: string | null;
  environment?: Environment | null;
};

export type GithubFilters = {
  provider: Provider | "all";
  region: Region | "all";
  environment: Environment | "all";
  repo: string | null;
  workflow: string | null;
  run: string | null;
  tab: string;
};

export const GITHUB_REPO_TABS = ["overview", "applications", "environments", "workflows", "variables", "secrets"] as const;
export type GithubRepoTab = (typeof GITHUB_REPO_TABS)[number];

export const GITHUB_SECRET_MASK = "••••••••••••";

export function githubHref(filters?: Partial<GithubFilters>): string {
  const params = new URLSearchParams();
  if (filters?.provider && filters.provider !== "all") params.set("provider", filters.provider.toLowerCase());
  if (filters?.region && filters.region !== "all") params.set("region", filters.region.toLowerCase());
  if (filters?.environment && filters.environment !== "all") {
    params.set("environment", filters.environment === "INT/TST" ? "int-tst" : filters.environment.toLowerCase());
  }
  if (filters?.repo) params.set("repo", filters.repo);
  if (filters?.workflow) params.set("workflow", filters.workflow);
  if (filters?.run) params.set("run", filters.run);
  if (filters?.tab && filters.tab !== "overview") params.set("tab", filters.tab);
  const query = params.toString();
  return query ? `/github?${query}` : "/github";
}

export function parseGithubFilters(search: Record<string, string | undefined>): GithubFilters {
  const provider = search.provider === "aws" ? "AWS" : search.provider === "alibaba" ? "Alibaba" : search.provider === "azure" ? "Azure" : search.provider === "gcp" ? "GCP" : "all";
  const regionMap: Record<string, Region> = { amer: "AMER", emea: "EMEA", apac: "APAC", china: "China" };
  return {
    provider,
    region: regionMap[search.region ?? ""] ?? "all",
    environment:
      search.environment === "int-tst"
        ? "INT/TST"
        : search.environment
          ? ((search.environment.toUpperCase() as Environment) ?? "all")
          : "all",
    repo: search.repo || null,
    workflow: search.workflow || null,
    run: search.run || null,
    tab: search.tab || "overview",
  };
}

export function formatDuration(seconds?: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export function shortSha(sha?: string | null): string {
  if (!sha) return "—";
  return sha.slice(0, 7);
}

export function githubQuery(query?: Record<string, string>): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}
