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
import { isPrdAlert, minutesAgo, type ManagedAlert } from "@/lib/alerts";
import type { Environment } from "@/lib/types";

export function AlertsConsole() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const selected = searchParams.get("selected");
  const [statusFilter, setStatusFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [environmentFilter, setEnvironmentFilter] = useState("");
  const [applicationFilter, setApplicationFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [nonce, setNonce] = useState(0);

  const listState = useResource(
    (signal) =>
      cloudOpsApi.managedAlerts(
        {
          ...(statusFilter ? { status: statusFilter } : {}),
          ...(severityFilter ? { severity: severityFilter } : {}),
          ...(providerFilter ? { provider: providerFilter } : {}),
          ...(regionFilter ? { region: regionFilter } : {}),
          ...(environmentFilter ? { environment: environmentFilter } : {}),
          ...(applicationFilter ? { application: applicationFilter } : {}),
          ...(typeFilter ? { type: typeFilter } : {}),
        },
        signal,
      ),
    [statusFilter, severityFilter, providerFilter, regionFilter, environmentFilter, applicationFilter, typeFilter, nonce],
  );

  function setSelected(id: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (id) params.set("selected", id);
    else params.delete("selected");
    router.push(`${pathname}?${params.toString()}`);
  }

  if (selected) {
    return <AlertDetails id={selected} onBack={() => setSelected(null)} onChanged={() => setNonce((value) => value + 1)} />;
  }

  return (
    <>
      <PageHeader title="Alerts" subtitle="Centralized operational alerts. Modules publish into one alerting system. Notifications are never sent directly by health, certificates, pipelines, or GitHub." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState state={listState} loadingLabel="Loading alerts…" emptyLabel="No alerts in the current filter." isEmpty={(data) => data.items.length === 0}>
            {(data) => (
              <>
                <KpiGrid>
                  <Kpi label="Critical" value={data.kpis.critical} tone={data.kpis.critical ? "critical" : undefined} />
                  <Kpi label="High" value={data.kpis.high} tone={data.kpis.high ? "warning" : undefined} />
                  <Kpi label="Medium" value={data.kpis.medium} />
                  <Kpi label="Acknowledged" value={data.kpis.acknowledged} />
                  <Kpi label="Suppressed" value={data.kpis.suppressed} />
                </KpiGrid>
                <CatalogPanel title="Open and historical alerts" hint="PRD rows are visually distinct. Secret values are never displayed.">
                  <div className="flex flex-wrap gap-2 border-b border-outline p-3">
                    <Filter placeholder="Status" value={statusFilter} onChange={setStatusFilter} />
                    <Filter placeholder="Severity" value={severityFilter} onChange={setSeverityFilter} />
                    <Filter placeholder="Provider" value={providerFilter} onChange={setProviderFilter} />
                    <Filter placeholder="Region" value={regionFilter} onChange={setRegionFilter} />
                    <Filter placeholder="Environment" value={environmentFilter} onChange={setEnvironmentFilter} />
                    <Filter placeholder="Application" value={applicationFilter} onChange={setApplicationFilter} />
                    <Filter placeholder="Type" value={typeFilter} onChange={setTypeFilter} />
                  </div>
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                        <th className="p-3">Severity</th>
                        <th className="p-3">Alert</th>
                        <th className="p-3">Application/Resource</th>
                        <th className="p-3">Provider</th>
                        <th className="p-3">Region</th>
                        <th className="p-3">Environment</th>
                        <th className="p-3">First Seen</th>
                        <th className="p-3">Last Seen</th>
                        <th className="p-3">Occurrences</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Owner</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((row) => (
                        <tr key={row.id} className={isPrdAlert(row) ? "border-b border-prd/30 bg-prd/5 hover:bg-prd/10" : "border-b border-outline hover:bg-surface-low"}>
                          <td className="p-3">
                            <StatusChip value={row.severity} />
                          </td>
                          <td className="p-3">
                            <button type="button" className="text-left font-semibold text-action hover:underline" onClick={() => setSelected(row.id)}>
                              {row.title}
                            </button>
                            <p className="font-mono text-[11px] text-muted">{row.alertType}</p>
                          </td>
                          <td className="p-3 font-mono text-xs text-muted">{row.objectName}</td>
                          <td className="p-3 text-muted">{row.provider}</td>
                          <td className="p-3 font-mono text-xs text-muted">{row.region}</td>
                          <td className="p-3">{row.environment ? <EnvBadge environment={row.environment as Environment} /> : "—"}</td>
                          <td className="p-3 font-mono text-xs text-muted">{row.age || minutesAgo(row.firstSeenAt)}</td>
                          <td className="p-3 font-mono text-xs text-muted">{minutesAgo(row.lastSeenAt)}</td>
                          <td className="p-3 font-mono text-xs">{row.occurrenceCount}</td>
                          <td className="p-3">
                            <StatusChip value={row.status} />
                          </td>
                          <td className="p-3 font-mono text-xs text-muted">{row.acknowledgedBy || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CatalogPanel>
              </>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function AlertDetails({ id, onBack, onChanged }: { id: string; onBack: () => void; onChanged: () => void }) {
  const [comment, setComment] = useState("Investigating");
  const [message, setMessage] = useState("");
  const [nonce, setNonce] = useState(0);
  const state = useResource((signal) => cloudOpsApi.managedAlert(id, signal), [id, nonce]);

  async function run(action: "acknowledge" | "resolve" | "suppress") {
    setMessage("");
    try {
      if (action === "acknowledge") await cloudOpsApi.acknowledgeAlert(id, comment);
      if (action === "resolve") await cloudOpsApi.resolveAlert(id, comment);
      if (action === "suppress") await cloudOpsApi.suppressAlert(id, comment);
      onChanged();
      setNonce((value) => value + 1);
      setMessage("Updated.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Action failed.");
    }
  }

  return (
    <>
      <PageHeader title="Alert details" subtitle="Central alert record, timeline, and notification history." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <button type="button" className="text-sm font-semibold text-action hover:underline" onClick={onBack}>
            ← Back to alerts
          </button>
          <QueryState state={state} loadingLabel="Loading alert…" emptyLabel="Alert not found.">
            {(alert: ManagedAlert) => (
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <div className="space-y-6 xl:col-span-2">
                  <CatalogPanel title={alert.title} hint={`${alert.provider} / ${alert.region} / ${alert.environment}`}>
                    <div className="grid grid-cols-2 gap-4 p-4 md:grid-cols-4">
                      <Meta label="Severity" value={<StatusChip value={alert.severity} />} />
                      <Meta label="Status" value={<StatusChip value={alert.status} />} />
                      <Meta label="Application" value={alert.applicationId || "—"} />
                      <Meta label="Resource" value={alert.objectName} />
                    </div>
                    <div className="space-y-3 border-t border-outline p-4">
                      <p className="text-sm text-ink">{alert.summary}</p>
                      <p className="font-mono text-xs text-muted">Fingerprint {alert.fingerprint.slice(0, 16)} · {alert.occurrenceCount} occurrences</p>
                    </div>
                  </CatalogPanel>
                  <CatalogPanel title="Evidence and related" hint="Links to related operational objects. Secret values are never displayed.">
                    <div className="grid grid-cols-1 gap-3 p-4 md:grid-cols-2">
                      <Related label="Incident" href={alert.related?.incident ? `/health-checks?incident=${alert.related.incident.id}` : null} value={alert.related?.incident?.title} />
                      <Related label="Pipeline" href={alert.related?.pipeline ? `/pipelines?selected=${alert.related.pipeline.id}` : null} value={alert.related?.pipeline?.name} />
                      <Related label="Certificate" href={alert.related?.certificate ? `/certificates?selected=${alert.related.certificate.id}` : null} value={alert.related?.certificate?.domain} />
                      <Related label="Deployment" href={null} value={alert.related?.deploymentId} />
                    </div>
                  </CatalogPanel>
                  <CatalogPanel title="Timeline" hint="Event-based alert history.">
                    <ul className="divide-y divide-outline">
                      {(alert.timeline || []).map((event) => (
                        <li key={event.id} className="px-4 py-3">
                          <p className="text-sm font-semibold text-ink">{event.title}</p>
                          <p className="font-mono text-xs text-muted">{event.detail || event.eventType}</p>
                          <p className="mt-1 text-[11px] text-muted">{event.createdAt} · {event.actor}</p>
                        </li>
                      ))}
                    </ul>
                  </CatalogPanel>
                </div>
                <div className="space-y-6">
                  <CatalogPanel title="Actions" hint="Acknowledgement does not resolve the alert.">
                    <div className="space-y-3 p-4">
                      <textarea className="w-full rounded border border-outline p-2 text-sm" rows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
                      <div className="flex flex-wrap gap-2">
                        <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" onClick={() => run("acknowledge")}>
                          Acknowledge
                        </button>
                        <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs font-semibold" onClick={() => run("suppress")}>
                          Suppress
                        </button>
                        <button type="button" className="rounded border border-prd px-3 py-1.5 text-xs font-semibold text-prd" onClick={() => run("resolve")}>
                          Resolve
                        </button>
                      </div>
                      {message ? <p className="text-xs text-muted">{message}</p> : null}
                    </div>
                  </CatalogPanel>
                  <CatalogPanel title="Notification history" hint="Delivery status only. Webhook URLs and tokens are never shown.">
                    <ul className="divide-y divide-outline">
                      {(alert.notifications || []).map((item) => (
                        <li key={item.id} className="px-4 py-3">
                          <p className="text-sm font-semibold text-ink">{item.destinationName || item.destinationId}</p>
                          <p className="font-mono text-xs text-muted">
                            {item.notificationType} · {item.status} · attempt {item.attempt}
                          </p>
                          {item.errorCategory ? <p className="text-xs text-critical">{item.errorCategory}</p> : null}
                        </li>
                      ))}
                    </ul>
                  </CatalogPanel>
                </div>
              </div>
            )}
          </QueryState>
        </div>
      </main>
    </>
  );
}

function Filter({ placeholder, value, onChange }: { placeholder: string; value: string; onChange: (value: string) => void }) {
  return (
    <input
      className="rounded border border-outline px-2 py-1 text-xs"
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-muted">{label}</p>
      <div className="mt-1 text-sm">{value}</div>
    </div>
  );
}

function Related({ label, href, value }: { label: string; href: string | null; value?: string | null }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase text-muted">{label}</p>
      {href && value ? (
        <Link href={href} className="text-sm font-semibold text-action hover:underline">
          {value}
        </Link>
      ) : (
        <p className="text-sm text-muted">{value || "—"}</p>
      )}
    </div>
  );
}
