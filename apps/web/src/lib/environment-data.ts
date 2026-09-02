import { isProductionEnvironment, regionsForProvider } from "./dashboard";
import type { EnvironmentIdentity, EnvironmentRecord } from "./domain";
import { ENVIRONMENTS, type Environment, type KpiSummary, type Provider, type Region } from "./types";

export type { EnvironmentIdentity, EnvironmentRecord };

const CLOUD_REGIONS: Record<string, string> = {
  "AWS-AMER": "us-east-1",
  "AWS-EMEA": "eu-west-1",
  "AWS-APAC": "ap-southeast-1",
  "Alibaba-China": "cn-hangzhou",
};

function accountName(provider: Provider, region: Region, environment: Environment): string {
  const classLabel = isProductionEnvironment(environment) ? "prod" : "nonprod";
  return provider === "Alibaba" ? `${classLabel}-china` : `${classLabel}-${region.toLowerCase()}`;
}

function clusterName(provider: Provider, region: Region, environment: Environment): string {
  const cloud = CLOUD_REGIONS[`${provider}-${region}`];
  const env = environment === "INT/TST" ? "int" : environment.toLowerCase();
  const suffix = provider === "Alibaba" ? "ack" : "k8s";
  return `${cloud}-${env}-${suffix}`;
}

export function getEnvironmentIdentity(
  provider: Provider,
  region: Region,
  environment: Environment,
): EnvironmentIdentity {
  return {
    provider,
    region,
    environment,
    platform: provider === "Alibaba" ? "ACK" : "EKS",
    cloudRegion: CLOUD_REGIONS[`${provider}-${region}`] ?? "",
    account: accountName(provider, region, environment),
    clusterName: clusterName(provider, region, environment),
  };
}

export function listEnvironmentIdentities(): EnvironmentIdentity[] {
  return (["AWS", "Alibaba"] as Provider[]).flatMap((provider) =>
    regionsForProvider(provider).flatMap((region) =>
      ENVIRONMENTS.map((environment) => getEnvironmentIdentity(provider, region, environment)),
    ),
  );
}

export function environmentTitle(identity: EnvironmentIdentity): string {
  return `${identity.provider} ${identity.region} ${identity.environment}`;
}

export function summarizeEnvironment(record: EnvironmentRecord): KpiSummary {
  const degradedApps = record.applications.filter((app) => app.issue !== "Healthy").length;
  const healthyApps = record.applications.filter((app) => app.issue === "Healthy").length;
  return {
    clustersHealthy: record.clusters.filter((cluster) => cluster.status === "Healthy").length,
    clustersDegraded: record.clusters.filter((cluster) => cluster.status === "Degraded").length,
    clustersUnreachable: record.clusters.filter((cluster) => cluster.status === "Unreachable").length,
    appsHealthy: healthyApps,
    appsDegraded: degradedApps,
    certsExpiring14d: record.certificates.length,
    secretsOverdue: record.secrets.filter((secret) => secret.status === "Overdue").length,
    failedDeploys: record.deployments.filter((item) => /fail/i.test(item.title)).length,
    githubFailures: record.github.filter((item) => /fail/i.test(item.title)).length,
    pipelineFailures: record.pipelines.filter((item) => /fail/i.test(item.title)).length,
    openAlerts: record.alerts.length,
  };
}
