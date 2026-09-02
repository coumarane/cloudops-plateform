import Link from "next/link";
import { EnvironmentKpis } from "@/components/environment/EnvironmentKpis";
import {
  ActivityList,
  ApplicationsTable,
  CertificatesTable,
  ClustersTable,
  OverviewActivity,
  OverviewAlerts,
  OverviewCertificates,
  OverviewSecrets,
  Panel,
  SecretsTable,
} from "@/components/environment/EnvironmentPanels";
import { certificatesHref } from "@/lib/certificates";
import { catalogHref } from "@/lib/catalog";
import { environmentHref, type EnvironmentTab } from "@/lib/environment";
import { secretsHref } from "@/lib/secrets";
import { summarizeEnvironment, type EnvironmentRecord } from "@/lib/environment-data";
import { StatusChip } from "@/components/catalog/CatalogChrome";

export function EnvironmentTabContent({
  record,
  tab,
}: {
  record: EnvironmentRecord;
  tab: EnvironmentTab;
}) {
  const summary = summarizeEnvironment(record);
  const { identity } = record;

  if (tab === "overview") {
    const degradedApps = record.applications.filter((app) => app.issue !== "Healthy");
    return (
      <div className="space-y-8">
        <EnvironmentKpis summary={summary} />
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-12">
          <div className="flex flex-col gap-8 xl:col-span-8">
            <Panel
              title="Clusters"
              action={
                <Link
                  href={environmentHref(identity.provider, identity.region, identity.environment, "clusters")}
                  className="text-xs font-semibold text-action hover:underline"
                >
                  View all
                </Link>
              }
            >
              <ClustersTable clusters={record.clusters} identity={identity} />
            </Panel>
            <Panel
              title={
                <span className="flex items-center gap-2">
                  Applications
                  {degradedApps.length > 0 ? (
                    <span className="rounded bg-surface-low px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted">
                      Degraded only
                    </span>
                  ) : null}
                </span>
              }
              action={
                <Link
                  href={environmentHref(identity.provider, identity.region, identity.environment, "applications")}
                  className="text-xs font-semibold text-action hover:underline"
                >
                  View all apps
                </Link>
              }
            >
              <ApplicationsTable
                applications={record.applications}
                degradedOnly={degradedApps.length > 0}
              />
            </Panel>
          </div>
          <div className="flex flex-col gap-4 xl:col-span-4">
            <OverviewAlerts record={record} />
            <OverviewSecrets record={record} />
            <OverviewCertificates record={record} />
            <OverviewActivity record={record} />
          </div>
        </div>
      </div>
    );
  }

  if (tab === "clusters") {
    return (
      <Panel
        title="Clusters"
        action={
          <Link
            href={catalogHref("/clusters", {
              provider: identity.provider,
              region: identity.region,
              environment: identity.environment,
            })}
            className="text-xs font-semibold text-action hover:underline"
          >
            Open Clusters
          </Link>
        }
      >
        <ClustersTable clusters={record.clusters} identity={identity} />
      </Panel>
    );
  }

  if (tab === "applications") {
    return (
      <Panel
        title="Applications"
        action={
          <Link
            href={catalogHref("/applications", {
              provider: identity.provider,
              region: identity.region,
              environment: identity.environment,
            })}
            className="text-xs font-semibold text-action hover:underline"
          >
            Open Applications
          </Link>
        }
      >
        <ApplicationsTable applications={record.applications} />
      </Panel>
    );
  }

  if (tab === "secrets") {
    return (
      <Panel
        title="Secrets"
        action={
          <Link
            href={secretsHref({
              provider: identity.provider,
              region: identity.region,
              account: identity.account,
              environment: identity.environment,
            })}
            className="text-xs font-semibold text-action hover:underline"
          >
            Open Secrets Management
          </Link>
        }
      >
        <p className="border-b border-outline px-4 py-2 text-xs text-muted">
          Rotation state and due dates only. Secret values are never displayed.
        </p>
        <SecretsTable secrets={record.secrets} />
      </Panel>
    );
  }

  if (tab === "certificates") {
    return (
      <Panel
        title="Certificates"
        action={
          <Link
            href={certificatesHref({
              provider: identity.provider,
              region: identity.region,
              environment: identity.environment,
            })}
            className="text-xs font-semibold text-action hover:underline"
          >
            Open Certificate Monitoring
          </Link>
        }
      >
        <p className="border-b border-outline px-4 py-2 text-xs text-muted">
          {identity.certificateTotal != null
            ? `${identity.certificateTotal} total · ${identity.certificateWarning ?? 0} warning · ${identity.certificateCritical ?? 0} critical. Expiration metadata only. Private keys are never displayed.`
            : "Expiration metadata only. Private keys are never displayed."}
        </p>
        <CertificatesTable certificates={record.certificates} />
      </Panel>
    );
  }

  if (tab === "deployments") {
    return (
      <Panel
        title="Deployments"
        action={<CatalogLink path="/deployments" identity={identity} label="Open Deployments" />}
      >
        <ActivityList items={record.deployments} empty="No deployments recorded for this environment." />
      </Panel>
    );
  }

  if (tab === "pipelines") {
    return (
      <Panel title="Pipelines" action={<CatalogLink path="/pipelines" identity={identity} label="Open Pipelines" />}>
        <ActivityList items={record.pipelines} empty="No pipelines recorded for this environment." />
      </Panel>
    );
  }

  if (tab === "github") {
    return (
      <Panel title="GitHub" action={<CatalogLink path="/github" identity={identity} label="Open GitHub" />}>
        <ActivityList items={record.github} empty="No GitHub workflow activity for this environment." />
      </Panel>
    );
  }

  if (tab === "health") {
    const identity = record.identity;
    const overall = identity.overallHealth || (record.applications.some((app) => (app.healthStatus || app.issue) !== "HEALTHY" && app.issue !== "Healthy") ? "UNHEALTHY" : "HEALTHY");
    const total = identity.appsTotal ?? record.applications.length;
    const healthy = identity.appsHealthyCount ?? record.applications.filter((app) => (app.healthStatus || "HEALTHY") === "HEALTHY" || app.issue === "Healthy").length;
    const degraded = identity.appsDegradedCount ?? record.applications.filter((app) => app.healthStatus === "DEGRADED" || app.issue === "Degraded").length;
    const unhealthy = identity.appsUnhealthyCount ?? 0;
    const critical = identity.appsCriticalCount ?? 0;
    const sorted = [...record.applications].sort((a, b) => (a.healthStatus || a.issue).localeCompare(b.healthStatus || b.issue));
    return (
      <div className="space-y-6">
        <Panel title={`${identity.provider} / ${identity.region} / ${identity.environment}`}>
          <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-4">
            <div>
              <p className="text-[10px] font-bold uppercase text-muted">Overall</p>
              <StatusChip value={overall} />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase text-muted">Clusters</p>
              <p className="text-sm">{record.clusters.filter((cluster) => cluster.status === "Healthy").length} healthy</p>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase text-muted">Applications</p>
              <p className="font-mono text-xs text-muted">
                {total} total · {healthy} healthy · {degraded} degraded · {unhealthy} unhealthy · {critical} critical
              </p>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase text-muted">Certificates / pipelines / incidents</p>
              <p className="font-mono text-xs text-muted">
                {identity.certificateCritical ?? 0} cert critical · {identity.pipelinesFailedRecently ?? 0} pipeline failed · {identity.openIncidents ?? 0} open incidents
              </p>
            </div>
          </div>
        </Panel>
        <Panel title="Applications by health" action={<CatalogLink path="/health-checks" identity={identity} label="Open Health" />}>
          <ApplicationsTable applications={sorted} />
        </Panel>
        <Panel title="Health events">
          <ActivityList items={record.health} empty="No health events for this environment." />
        </Panel>
      </div>
    );
  }

  return (
    <Panel title="Audit" action={<CatalogLink path="/audit" identity={identity} label="Open Audit" />}>
      <ActivityList items={record.audit} empty="No audit events for this environment." />
    </Panel>
  );
}

function CatalogLink({
  path,
  identity,
  label,
}: {
  path: string;
  identity: EnvironmentRecord["identity"];
  label: string;
}) {
  return (
    <Link
      href={catalogHref(path, {
        provider: identity.provider,
        region: identity.region,
        environment: identity.environment,
      })}
      className="text-xs font-semibold text-action hover:underline"
    >
      {label}
    </Link>
  );
}
