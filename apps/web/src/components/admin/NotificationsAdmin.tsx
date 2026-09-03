"use client";

import { useState } from "react";
import {
  AdminDialog,
  AdminField,
  AdminSelect,
  AdminTabs,
  EmptyCatalog,
  GhostButton,
  PrimaryButton,
} from "@/components/admin/AdminChrome";
import { CatalogPanel, StatusChip } from "@/components/catalog/CatalogChrome";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import type { AlertRoutingRule, MaintenanceWindow, NotificationDestination, NotificationPolicy } from "@/lib/alerts";

const TABS = ["Destinations", "Policies", "Routing", "Maintenance Windows"] as const;
type Tab = (typeof TABS)[number];
const LABELS: Record<Tab, string> = {
  Destinations: "Destinations",
  Policies: "Policies",
  Routing: "Routing",
  "Maintenance Windows": "Maintenance Windows",
};

export function NotificationsAdmin({ onNotice }: { onNotice?: (message: string) => void }) {
  const [tab, setTab] = useState<Tab>("Destinations");
  const [nonce, setNonce] = useState(0);
  const destinations = useResource((signal) => cloudOpsApi.notificationDestinations(signal), [nonce]);
  const policies = useResource((signal) => cloudOpsApi.notificationPolicies(signal), [nonce]);
  const routes = useResource((signal) => cloudOpsApi.alertRoutingRules(signal), [nonce]);
  const windows = useResource((signal) => cloudOpsApi.maintenanceWindows(signal), [nonce]);

  return (
    <CatalogPanel title="Notifications" hint="Destinations, policies, routing, and maintenance windows. Webhook URLs, tokens, and SMTP passwords are write-only and never redisplayed.">
      <div className="px-4">
        <AdminTabs items={TABS} value={tab} labels={LABELS} onChange={setTab} ariaLabel="Notification configuration" />
      </div>
      {tab === "Destinations" ? (
        <DestinationsPanel
          items={destinations.status === "success" ? destinations.data.items : []}
          onChanged={() => setNonce((value) => value + 1)}
          onNotice={onNotice}
        />
      ) : null}
      {tab === "Policies" ? <PoliciesPanel items={policies.status === "success" ? policies.data.items : []} /> : null}
      {tab === "Routing" ? <RoutingPanel items={routes.status === "success" ? routes.data.items : []} /> : null}
      {tab === "Maintenance Windows" ? (
        <WindowsPanel items={windows.status === "success" ? windows.data.items : []} onChanged={() => setNonce((value) => value + 1)} onNotice={onNotice} />
      ) : null}
    </CatalogPanel>
  );
}

function DestinationsPanel({
  items,
  onChanged,
  onNotice,
}: {
  items: NotificationDestination[];
  onChanged: () => void;
  onNotice?: (message: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState("email");
  const [description, setDescription] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [to, setTo] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function create() {
    setError("");
    setBusy(true);
    try {
      await cloudOpsApi.createNotificationDestination({
        name,
        providerType,
        description,
        secretValue: secretValue || undefined,
        config: to ? { to } : {},
      });
      setName("");
      setSecretValue("");
      setTo("");
      setDescription("");
      setOpen(false);
      onChanged();
      onNotice?.("Destination saved. Secret values are not redisplayed.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save destination.");
    } finally {
      setBusy(false);
    }
  }

  async function test(id: string) {
    try {
      const result = await cloudOpsApi.testNotificationDestination(id);
      onNotice?.(`Test ${result.status}.`);
    } catch (error) {
      onNotice?.(error instanceof Error ? error.message : "Test failed.");
    }
  }

  return (
    <>
      <div className="flex justify-end border-b border-outline px-4 py-3">
        <PrimaryButton onClick={() => setOpen(true)}>Add destination</PrimaryButton>
      </div>
      {items.length === 0 ? (
        <EmptyCatalog
          title="No notification destinations"
          description="Add email, Slack, Teams, webhook, or log destinations. Secret values are write-only."
          action="Add destination"
          onClick={() => setOpen(true)}
        />
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
              <th className="p-3">Name</th>
              <th className="p-3">Type</th>
              <th className="p-3">Secret</th>
              <th className="p-3">Enabled</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-outline hover:bg-surface-low/70">
                <td className="p-3 font-semibold">{item.name}</td>
                <td className="p-3 font-mono text-xs">{item.providerType}</td>
                <td className="p-3 text-xs text-muted">{item.hasSecret ? "configured" : "none"}</td>
                <td className="p-3">
                  <StatusChip value={item.enabled ? "Connected" : "disabled"} />
                </td>
                <td className="p-3">
                  <button type="button" className="text-xs font-semibold text-action hover:underline" onClick={() => void test(item.id)}>
                    Test
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {open ? (
        <AdminDialog
          title="Add destination"
          hint="Webhook URLs, tokens, and SMTP passwords are write-only and never redisplayed."
          onClose={() => setOpen(false)}
          footer={
            <>
              <GhostButton onClick={() => setOpen(false)}>Cancel</GhostButton>
              <PrimaryButton disabled={busy || !name} onClick={() => void create()}>{busy ? "Saving…" : "Save destination"}</PrimaryButton>
            </>
          }
        >
          <div className="grid gap-4">
            <AdminField label="Name" value={name} onChange={setName} />
            <AdminSelect label="Type" value={providerType} onChange={setProviderType}>
              <option value="email">Email</option>
              <option value="slack">Slack</option>
              <option value="teams">Teams</option>
              <option value="webhook">Webhook</option>
              <option value="log">Log</option>
            </AdminSelect>
            <AdminField label="Description" value={description} onChange={setDescription} />
            <AdminField label="Recipient (email)" value={to} onChange={setTo} />
            <AdminField label="Webhook URL / token / SMTP password" value={secretValue} onChange={setSecretValue} type="password" autoComplete="new-password" />
            {error ? <p className="text-sm text-critical">{error}</p> : null}
          </div>
        </AdminDialog>
      ) : null}
    </>
  );
}

function PoliciesPanel({ items }: { items: NotificationPolicy[] }) {
  if (items.length === 0) {
    return <p className="p-6 text-sm text-muted">No notification policies configured.</p>;
  }
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
          <th className="p-3">Policy</th>
          <th className="p-3">Initial</th>
          <th className="p-3">Repeat</th>
          <th className="p-3">Escalate</th>
          <th className="p-3">Recovery</th>
          <th className="p-3">Steps</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} className="border-b border-outline hover:bg-surface-low/70">
            <td className="p-3 font-semibold">{item.name}</td>
            <td className="p-3">{item.initialEnabled ? "Yes" : "No"}</td>
            <td className="p-3 font-mono text-xs">{item.repeatAfterSeconds}s</td>
            <td className="p-3 font-mono text-xs">{item.escalateAfterSeconds}s</td>
            <td className="p-3">{item.recoveryEnabled ? "Yes" : "No"}</td>
            <td className="p-3 font-mono text-xs">{item.steps.map((step) => `${step.stepType}@${step.delaySeconds}s`).join(", ") || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RoutingPanel({ items }: { items: AlertRoutingRule[] }) {
  if (items.length === 0) {
    return <p className="p-6 text-sm text-muted">No alert routing rules configured.</p>;
  }
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
          <th className="p-3">Route</th>
          <th className="p-3">Provider</th>
          <th className="p-3">Region</th>
          <th className="p-3">Environment</th>
          <th className="p-3">Application</th>
          <th className="p-3">Severity</th>
          <th className="p-3">Destination</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} className={item.environmentFilter === "PRD" ? "border-b border-prd/30 bg-prd/5" : "border-b border-outline hover:bg-surface-low/70"}>
            <td className="p-3 font-semibold">{item.name}</td>
            <td className="p-3">{item.providerFilter || "any"}</td>
            <td className="p-3">{item.regionFilter || "any"}</td>
            <td className="p-3">{item.environmentFilter || "any"}</td>
            <td className="p-3 font-mono text-xs">{item.applicationFilter || "any"}</td>
            <td className="p-3">{item.severityFilter || "any"}</td>
            <td className="p-3 font-mono text-xs">{item.destinationId}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function WindowsPanel({
  items,
  onChanged,
  onNotice,
}: {
  items: MaintenanceWindow[];
  onChanged: () => void;
  onNotice?: (message: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("PRD payments deployment");
  const [environment, setEnvironment] = useState("PRD");
  const [application, setApplication] = useState("payments-api");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function create() {
    setError("");
    setBusy(true);
    try {
      await cloudOpsApi.createMaintenanceWindow({
        name,
        provider: "AWS",
        region: "EMEA",
        environment,
        application,
        startsAt: new Date(startsAt).toISOString(),
        endsAt: new Date(endsAt).toISOString(),
        reason,
        changeTicket: "",
      });
      setOpen(false);
      onChanged();
      onNotice?.("Maintenance window created. Notifications are suppressed during the window.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create window.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="flex justify-end border-b border-outline px-4 py-3">
        <PrimaryButton onClick={() => setOpen(true)}>Add window</PrimaryButton>
      </div>
      {items.length === 0 ? (
        <EmptyCatalog
          title="No maintenance windows"
          description="Create a one-time window to suppress notifications during a planned change."
          action="Add window"
          onClick={() => setOpen(true)}
        />
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
              <th className="p-3">Window</th>
              <th className="p-3">Scope</th>
              <th className="p-3">Starts</th>
              <th className="p-3">Ends</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-outline hover:bg-surface-low/70">
                <td className="p-3 font-semibold">{item.name}</td>
                <td className="p-3 font-mono text-xs">
                  {item.provider} {item.region} {item.environment} {item.application}
                </td>
                <td className="p-3 font-mono text-xs">{item.startsAt}</td>
                <td className="p-3 font-mono text-xs">{item.endsAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {open ? (
        <AdminDialog
          title="Add maintenance window"
          hint="Notifications are suppressed during the window. Secret values are not stored here."
          onClose={() => setOpen(false)}
          footer={
            <>
              <GhostButton onClick={() => setOpen(false)}>Cancel</GhostButton>
              <PrimaryButton disabled={busy || !name || !startsAt || !endsAt} onClick={() => void create()}>
                {busy ? "Saving…" : "Create window"}
              </PrimaryButton>
            </>
          }
        >
          <div className="grid gap-4">
            <AdminField label="Name" value={name} onChange={setName} />
            <AdminField label="Environment" value={environment} onChange={setEnvironment} />
            <AdminField label="Application" value={application} onChange={setApplication} />
            <AdminField label="Starts" value={startsAt} onChange={setStartsAt} type="datetime-local" />
            <AdminField label="Ends" value={endsAt} onChange={setEndsAt} type="datetime-local" />
            <AdminField label="Reason" value={reason} onChange={setReason} />
            {error ? <p className="text-sm text-critical">{error}</p> : null}
          </div>
        </AdminDialog>
      ) : null}
    </>
  );
}
