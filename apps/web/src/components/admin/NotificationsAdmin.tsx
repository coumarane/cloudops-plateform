"use client";

import { useState } from "react";
import { CatalogPanel, StatusChip } from "@/components/catalog/CatalogChrome";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import type { AlertRoutingRule, MaintenanceWindow, NotificationDestination, NotificationPolicy } from "@/lib/alerts";

const TABS = ["Destinations", "Policies", "Routing", "Maintenance Windows"] as const;

export function NotificationsAdmin() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Destinations");
  const [nonce, setNonce] = useState(0);
  const destinations = useResource((signal) => cloudOpsApi.notificationDestinations(signal), [nonce]);
  const policies = useResource((signal) => cloudOpsApi.notificationPolicies(signal), [nonce]);
  const routes = useResource((signal) => cloudOpsApi.alertRoutingRules(signal), [nonce]);
  const windows = useResource((signal) => cloudOpsApi.maintenanceWindows(signal), [nonce]);

  return (
    <CatalogPanel title="Notifications" hint="Destinations, policies, routing, and maintenance windows. Webhook URLs, tokens, and SMTP passwords are write-only and never redisplayed.">
      <div className="flex flex-wrap gap-2 border-b border-outline p-3">
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            className={tab === item ? "rounded bg-action px-3 py-1 text-xs font-semibold text-white" : "rounded border border-outline px-3 py-1 text-xs"}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </div>
      {tab === "Destinations" ? (
        <DestinationsPanel
          items={destinations.status === "success" ? destinations.data.items : []}
          onChanged={() => setNonce((value) => value + 1)}
        />
      ) : null}
      {tab === "Policies" ? <PoliciesPanel items={policies.status === "success" ? policies.data.items : []} /> : null}
      {tab === "Routing" ? <RoutingPanel items={routes.status === "success" ? routes.data.items : []} /> : null}
      {tab === "Maintenance Windows" ? (
        <WindowsPanel items={windows.status === "success" ? windows.data.items : []} onChanged={() => setNonce((value) => value + 1)} />
      ) : null}
    </CatalogPanel>
  );
}

function DestinationsPanel({ items, onChanged }: { items: NotificationDestination[]; onChanged: () => void }) {
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState("email");
  const [description, setDescription] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [to, setTo] = useState("");
  const [message, setMessage] = useState("");

  async function create() {
    setMessage("");
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
      onChanged();
      setMessage("Destination saved. Secret values are not redisplayed.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save destination.");
    }
  }

  async function test(id: string) {
    setMessage("");
    try {
      const result = await cloudOpsApi.testNotificationDestination(id);
      setMessage(`Test ${result.status}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Test failed.");
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 p-4 xl:grid-cols-2">
      <div>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
              <th className="p-2">Name</th>
              <th className="p-2">Type</th>
              <th className="p-2">Secret</th>
              <th className="p-2">Enabled</th>
              <th className="p-2" />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-outline">
                <td className="p-2 font-semibold">{item.name}</td>
                <td className="p-2 font-mono text-xs">{item.providerType}</td>
                <td className="p-2 text-xs text-muted">{item.hasSecret ? "configured" : "none"}</td>
                <td className="p-2">
                  <StatusChip value={item.enabled ? "Connected" : "disabled"} />
                </td>
                <td className="p-2">
                  <button type="button" className="text-xs font-semibold text-action hover:underline" onClick={() => test(item.id)}>
                    Test
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <form
        className="space-y-3 rounded border border-outline p-4"
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <p className="text-sm font-semibold">New destination</p>
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" placeholder="Name" value={name} onChange={(event) => setName(event.target.value)} required />
        <select className="w-full rounded border border-outline px-2 py-1 text-sm" value={providerType} onChange={(event) => setProviderType(event.target.value)}>
          <option value="email">Email</option>
          <option value="slack">Slack</option>
          <option value="teams">Teams</option>
          <option value="webhook">Webhook</option>
          <option value="log">Log</option>
        </select>
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" placeholder="Description" value={description} onChange={(event) => setDescription(event.target.value)} />
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" placeholder="Recipient (email)" value={to} onChange={(event) => setTo(event.target.value)} />
        <input
          className="w-full rounded border border-outline px-2 py-1 text-sm"
          placeholder="Webhook URL / token / SMTP password"
          type="password"
          autoComplete="new-password"
          value={secretValue}
          onChange={(event) => setSecretValue(event.target.value)}
        />
        <p className="text-[11px] text-muted">Write-only. Existing secrets are never shown again.</p>
        <button type="submit" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
          Save destination
        </button>
        {message ? <p className="text-xs text-muted">{message}</p> : null}
      </form>
    </div>
  );
}

function PoliciesPanel({ items }: { items: NotificationPolicy[] }) {
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
          <tr key={item.id} className="border-b border-outline">
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
          <tr key={item.id} className={item.environmentFilter === "PRD" ? "border-b border-prd/30 bg-prd/5" : "border-b border-outline"}>
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

function WindowsPanel({ items, onChanged }: { items: MaintenanceWindow[]; onChanged: () => void }) {
  const [name, setName] = useState("PRD payments deployment");
  const [environment, setEnvironment] = useState("PRD");
  const [application, setApplication] = useState("payments-api");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");

  async function create() {
    setMessage("");
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
      onChanged();
      setMessage("Maintenance window created. Notifications are suppressed during the window.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create window.");
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 p-4 xl:grid-cols-2">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase text-muted">
            <th className="p-2">Window</th>
            <th className="p-2">Scope</th>
            <th className="p-2">Starts</th>
            <th className="p-2">Ends</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-b border-outline">
              <td className="p-2 font-semibold">{item.name}</td>
              <td className="p-2 font-mono text-xs">
                {item.provider} {item.region} {item.environment} {item.application}
              </td>
              <td className="p-2 font-mono text-xs">{item.startsAt}</td>
              <td className="p-2 font-mono text-xs">{item.endsAt}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <form
        className="space-y-3 rounded border border-outline p-4"
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <p className="text-sm font-semibold">New one-time window</p>
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" value={name} onChange={(event) => setName(event.target.value)} required />
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" value={environment} onChange={(event) => setEnvironment(event.target.value)} />
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" value={application} onChange={(event) => setApplication(event.target.value)} />
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} required />
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" type="datetime-local" value={endsAt} onChange={(event) => setEndsAt(event.target.value)} required />
        <input className="w-full rounded border border-outline px-2 py-1 text-sm" placeholder="Reason" value={reason} onChange={(event) => setReason(event.target.value)} />
        <button type="submit" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
          Create window
        </button>
        {message ? <p className="text-xs text-muted">{message}</p> : null}
      </form>
    </div>
  );
}
