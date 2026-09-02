import Link from "next/link";
import type { ReactNode } from "react";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { environmentHref } from "@/lib/environment";
import { secretsHref } from "@/lib/secrets";
import type {
  EnvironmentActivity,
  EnvironmentApplication,
  EnvironmentCertificate,
  EnvironmentCluster,
  EnvironmentIdentity,
  EnvironmentRecord,
  EnvironmentSecret,
} from "@/lib/environment-data";

function Panel({
  title,
  action,
  children,
  tone,
}: {
  title: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  tone?: "critical";
}) {
  return (
    <section
      className={
        tone === "critical"
          ? "rounded border border-critical/30 bg-white"
          : "rounded border border-outline bg-white"
      }
    >
      <div
        className={
          tone === "critical"
            ? "flex items-center justify-between border-b border-critical/20 bg-critical/5 px-4 py-3"
            : "flex items-center justify-between border-b border-outline bg-surface-low px-4 py-3"
        }
      >
        <h2 className={tone === "critical" ? "text-[15px] font-semibold text-critical" : "text-[15px] font-semibold text-ink"}>
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function StatusChip({ status }: { status: EnvironmentCluster["status"] }) {
  if (status === "Unreachable") {
    return (
      <span className="inline-flex items-center rounded bg-critical/10 px-2 py-0.5 text-xs font-semibold text-critical">
        Unreachable
      </span>
    );
  }
  if (status === "Degraded") {
    return (
      <span className="inline-flex items-center rounded bg-warning/10 px-2 py-0.5 text-xs font-semibold text-warning">
        Degraded
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded bg-healthy/10 px-2 py-0.5 text-xs font-semibold text-healthy">
      Healthy
    </span>
  );
}

function SecretStatus({ status }: { status: EnvironmentSecret["status"] }) {
  if (status === "Overdue") {
    return <span className="rounded bg-warning/10 px-2 py-1 text-xs font-semibold text-warning">Overdue</span>;
  }
  if (status === "Due soon") {
    return <span className="rounded bg-warning/10 px-2 py-1 text-xs font-semibold text-warning">Due soon</span>;
  }
  return <span className="rounded bg-healthy/10 px-2 py-1 text-xs font-semibold text-healthy">OK</span>;
}

export function ClustersTable({
  clusters,
  identity,
}: {
  clusters: EnvironmentCluster[];
  identity: EnvironmentIdentity;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Cluster name</th>
            <th className="p-3">Type</th>
            <th className="p-3">Version</th>
            <th className="p-3">Nodes</th>
            <th className="p-3">Status</th>
            <th className="p-3">Apps</th>
            <th className="p-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {clusters.map((cluster) => (
            <tr key={cluster.name} className="border-b border-outline last:border-b-0">
              <td className="p-3 font-mono text-xs font-semibold text-ink">{cluster.name}</td>
              <td className="p-3 text-muted">{cluster.platform}</td>
              <td className="p-3 text-muted">{cluster.version}</td>
              <td className="p-3 text-muted">{cluster.nodes}</td>
              <td className="p-3">
                <StatusChip status={cluster.status} />
              </td>
              <td className="p-3 text-xs text-warning">{cluster.appsLabel}</td>
              <td className="p-3 text-right">
                <Link
                  href={environmentHref(identity.provider, identity.region, identity.environment, "clusters")}
                  className="rounded bg-sidebar px-3 py-1 text-xs font-semibold text-white hover:bg-ink"
                >
                  Investigate
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ApplicationsTable({
  applications,
  degradedOnly,
}: {
  applications: EnvironmentApplication[];
  degradedOnly?: boolean;
}) {
  const rows = degradedOnly ? applications.filter((app) => app.issue !== "Healthy") : applications;
  if (rows.length === 0) {
    return <p className="p-4 text-sm text-muted">No applications in this view.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Application</th>
            <th className="p-3">Namespace</th>
            <th className="p-3">Pods (ready/desired)</th>
            <th className="p-3">Issue</th>
            <th className="p-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((app) => (
            <tr key={app.name} className="border-b border-outline last:border-b-0">
              <td className="p-3 font-mono text-xs font-semibold text-ink">{app.name}</td>
              <td className="p-3 text-muted">{app.namespace}</td>
              <td className="p-3 font-mono text-xs">{app.replicas}</td>
              <td className="p-3">
                <span className={app.issue === "ImagePullBackOff" ? "text-xs text-critical" : "text-xs text-warning"}>
                  {app.issue === "Healthy" ? "—" : app.issue}
                </span>
              </td>
              <td className="p-3 text-right">
                <span className="text-xs font-semibold text-action">{app.action}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SecretsTable({ secrets }: { secrets: EnvironmentSecret[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Secret name</th>
            <th className="p-3">Namespace</th>
            <th className="p-3">Rotation</th>
            <th className="p-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {secrets.map((secret) => (
            <tr key={secret.name} className="border-b border-outline last:border-b-0">
              <td className="p-3 font-mono text-xs text-ink">{secret.name}</td>
              <td className="p-3 text-muted">{secret.namespace}</td>
              <td className="p-3 text-muted">{secret.detail}</td>
              <td className="p-3">
                <SecretStatus status={secret.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CertificatesTable({ certificates }: { certificates: EnvironmentCertificate[] }) {
  if (certificates.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-muted">
        <ShieldCheck className="mx-auto mb-2 h-6 w-6 text-outline" aria-hidden />
        All certificates healthy.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Certificate</th>
            <th className="p-3">Days to expiry</th>
          </tr>
        </thead>
        <tbody>
          {certificates.map((certificate) => (
            <tr key={certificate.name} className="border-b border-outline last:border-b-0">
              <td className="p-3 font-mono text-xs text-ink">{certificate.name}</td>
              <td className="p-3 font-semibold text-warning">{certificate.daysToExpiry}d</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ActivityList({ items, empty }: { items: EnvironmentActivity[]; empty: string }) {
  if (items.length === 0) {
    return <p className="p-4 text-sm text-muted">{empty}</p>;
  }

  return (
    <ul className="divide-y divide-outline">
      {items.map((item) => (
        <li key={`${item.title}-${item.age}`} className="p-3">
          <p className="text-sm font-semibold text-ink">{item.title}</p>
          <p className="mt-0.5 font-mono text-[11px] text-muted">{item.detail}</p>
          <p className="mt-1 text-[11px] text-muted">{item.age}</p>
        </li>
      ))}
    </ul>
  );
}

export function OverviewAlerts({ record }: { record: EnvironmentRecord }) {
  return (
    <Panel
      tone="critical"
      title={
        <span className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" aria-hidden />
          Operational Alerts
        </span>
      }
      action={
        <span className="rounded bg-critical px-1.5 py-0.5 text-[10px] font-bold text-white">{record.alerts.length}</span>
      }
    >
      {record.alerts.length === 0 ? (
        <p className="p-4 text-sm text-muted">No open alerts.</p>
      ) : (
        <div className="space-y-3 p-4">
          {record.alerts.map((alert) => (
            <article key={alert.title} className="rounded border border-critical/20 bg-critical/5 p-3">
              <p className="text-sm font-semibold text-ink">{alert.title}</p>
              <p className="mt-1 font-mono text-xs text-muted">{alert.objectName}</p>
              <p className="mt-2 text-[11px] text-muted">{alert.age}</p>
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

export function OverviewSecrets({ record }: { record: EnvironmentRecord }) {
  const actionNeeded = record.secrets.some((secret) => secret.status !== "OK");
  return (
    <Panel
      title="Secret Rotation"
      action={
        actionNeeded ? (
          <span className="rounded bg-surface-low px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-muted">
            Action needed
          </span>
        ) : null
      }
    >
      <div className="p-3">
        {record.secrets.map((secret) => (
          <div key={secret.name} className="flex items-center justify-between border-b border-outline py-2 last:border-b-0">
            <div>
              <p className="font-mono text-sm text-ink">{secret.name}</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted">Namespace: {secret.namespace}</p>
            </div>
            <SecretStatus status={secret.status} />
          </div>
        ))}
        <div className="mt-2 border-t border-dashed border-outline pt-2 text-center">
          <Link
            href={secretsHref({
              provider: record.identity.provider,
              region: record.identity.region,
              account: record.identity.account,
              environment: record.identity.environment,
            })}
            className="text-xs font-semibold text-action hover:underline"
          >
            Manage secrets
          </Link>
        </div>
      </div>
    </Panel>
  );
}

export function OverviewCertificates({ record }: { record: EnvironmentRecord }) {
  return (
    <Panel title="Certificates (next 30 days)">
      <CertificatesTable certificates={record.certificates} />
    </Panel>
  );
}

export function OverviewActivity({ record }: { record: EnvironmentRecord }) {
  return (
    <Panel title="Recent activity">
      <ActivityList items={record.recentActivity} empty="No recent activity." />
    </Panel>
  );
}

export { Panel };