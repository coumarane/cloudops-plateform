import type { Environment, Provider, Region } from "@/lib/types";
import { formatDuration, shortSha } from "@/lib/github";

export type PipelineProviderKey = "github-actions" | "azure-devops" | "gitlab" | "jenkins" | "mock";

export type PipelineRun = {
  id: string;
  pipelineId: string;
  pipelineName: string;
  providerKey: string;
  providerName: string;
  externalRunId: string;
  branch: string;
  commitSha: string;
  version: string;
  trigger: string;
  actor: string;
  status: string;
  providerStatus: string;
  startedAt?: string | null;
  completedAt?: string | null;
  durationSeconds?: number | null;
  externalUrl: string;
  applicationId: string;
  deploymentId: string;
  repositoryId: string;
  repository: string;
  clusterId: string;
  provider?: Provider | null;
  region?: Region | null;
  environment?: Environment | null;
  age?: string;
  stages?: PipelineStage[];
  jobs?: PipelineJob[];
};

export type PipelineStage = {
  id: string;
  runId: string;
  name: string;
  status: string;
  htmlUrl: string;
  durationSeconds?: number | null;
  sortOrder: number;
};

export type PipelineJob = {
  id: string;
  runId: string;
  stageId: string;
  name: string;
  status: string;
  htmlUrl: string;
  durationSeconds?: number | null;
};

export type PipelineEnvironmentMapping = {
  id: string;
  pipelineId: string;
  environmentId: string;
  branchPattern: string;
  stageName: string;
  active: boolean;
  priority: number;
  provider?: Provider | null;
  region?: Region | null;
  environment?: Environment | null;
};

export type Pipeline = {
  id: string;
  providerKey: string;
  providerName: string;
  name: string;
  repositoryId: string;
  repository: string;
  applicationId: string;
  applicationIds: string[];
  defaultBranch: string;
  enabled: boolean;
  htmlUrl: string;
  latestRun?: PipelineRun | null;
  successRate?: number | null;
  averageDurationSeconds?: number | null;
  mappedEnvironments: PipelineEnvironmentMapping[];
  provider?: Provider | null;
  region?: Region | null;
  environment?: Environment | null;
};

export type PipelineOverview = {
  pipelineRunsToday: number;
  runningPipelines: number;
  failedPipelines: number;
  failedPrdPipelines: number;
  averageDeploymentDurationSeconds: number;
  recentFailures: PipelineRun[];
};

export type PipelineFilters = {
  provider: Provider | "all";
  region: Region | "all";
  environment: Environment | "all";
  pipeline: string | null;
  run: string | null;
  tab: string;
};

export const PIPELINE_TABS = ["overview", "runs", "environments", "configuration"] as const;

export function pipelineHref(filters?: Partial<PipelineFilters>): string {
  const params = new URLSearchParams();
  if (filters?.pipeline) params.set("pipeline", filters.pipeline);
  if (filters?.run) params.set("run", filters.run);
  if (filters?.tab && filters.tab !== "overview") params.set("tab", filters.tab);
  const query = params.toString();
  return query ? `/pipelines?${query}` : "/pipelines";
}

export function parsePipelineFilters(search: Record<string, string | undefined>): PipelineFilters {
  const regionMap: Record<string, Region> = { amer: "AMER", emea: "EMEA", apac: "APAC", china: "China" };
  return {
    provider: search.provider === "aws" ? "AWS" : search.provider === "alibaba" ? "Alibaba" : search.provider === "azure" ? "Azure" : search.provider === "gcp" ? "GCP" : "all",
    region: regionMap[search.region ?? ""] ?? "all",
    environment:
      search.environment === "int-tst"
        ? "INT/TST"
        : search.environment
          ? ((search.environment.toUpperCase() as Environment) ?? "all")
          : "all",
    pipeline: search.pipeline || null,
    run: search.run || null,
    tab: search.tab || "overview",
  };
}

export function pipelineQuery(query?: Record<string, string>): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export function openInProviderLabel(providerKey?: string | null): string {
  if (providerKey === "azure-devops") return "Open in Azure DevOps";
  if (providerKey === "github-actions") return "Open in GitHub";
  return "Open in provider";
}

export { formatDuration, shortSha };
