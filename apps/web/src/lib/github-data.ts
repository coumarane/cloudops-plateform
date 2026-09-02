import { GITHUB_SECRET_MASK, type GithubOverview, type GithubVariable } from "./github";

export function emptyGithubOverview(): GithubOverview {
  return {
    repositories: 0,
    activeWorkflows: 0,
    runningWorkflows: 0,
    failedWorkflows: 0,
    failedWorkflowsLast24h: 0,
    succeededWorkflows: 0,
    unmappedRepositories: 0,
    unmappedGithubEnvironments: 0,
    recentFailures: [],
  };
}

export function displayVariableValue(variable: GithubVariable): string {
  if (variable.sensitive) return GITHUB_SECRET_MASK;
  return variable.value || GITHUB_SECRET_MASK;
}
