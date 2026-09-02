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
import { environmentHref, type EnvironmentTab } from "@/lib/environment";
import { secretsHref } from "@/lib/secrets";
import { summarizeEnvironment, type EnvironmentRecord } from "@/lib/environment-data";

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
      <Panel title="Clusters">
        <ClustersTable clusters={record.clusters} identity={identity} />
      </Panel>
    );
  }

  if (tab === "applications") {
    return (
      <Panel title="Applications">
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
          Expiration metadata only. Private keys are never displayed.
        </p>
        <CertificatesTable certificates={record.certificates} />
      </Panel>
    );
  }

  if (tab === "deployments") {
    return (
      <Panel title="Deployments">
        <ActivityList items={record.deployments} empty="No deployments recorded for this environment." />
      </Panel>
    );
  }

  if (tab === "pipelines") {
    return (
      <Panel title="Pipelines">
        <ActivityList items={record.pipelines} empty="No pipelines recorded for this environment." />
      </Panel>
    );
  }

  if (tab === "github") {
    return (
      <Panel title="GitHub">
        <ActivityList items={record.github} empty="No GitHub workflow activity for this environment." />
      </Panel>
    );
  }

  if (tab === "health") {
    return (
      <Panel title="Health">
        <ActivityList items={record.health} empty="No health events for this environment." />
      </Panel>
    );
  }

  return (
    <Panel title="Audit">
      <ActivityList items={record.audit} empty="No audit events for this environment." />
    </Panel>
  );
}
