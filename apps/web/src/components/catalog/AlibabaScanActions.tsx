"use client";

import { useState } from "react";
import { CatalogPanel } from "@/components/catalog/CatalogChrome";
import { cloudOpsApi } from "@/lib/api/client";

const ACTIONS = [
  {
    id: "validation",
    label: "Validate Alibaba accounts",
    hint: "RAM identity only. Secrets stay in the worker.",
    run: () => cloudOpsApi.triggerAlibabaAccountValidation(),
  },
  {
    id: "discovery",
    label: "Discover ACK clusters",
    hint: "China NonProd and Prod. PRD stays read-only.",
    run: () => cloudOpsApi.triggerAlibabaClusterDiscovery(),
  },
  {
    id: "health",
    label: "Scan ACK health",
    hint: "Shared Kubernetes collector",
    run: () => cloudOpsApi.triggerAlibabaHealthScan(),
  },
  {
    id: "certs",
    label: "Discover certificates",
    hint: "CAS and Kubernetes TLS metadata",
    run: () => cloudOpsApi.triggerAlibabaCertificateDiscovery(),
  },
  {
    id: "expiry",
    label: "Scan certificate expiry",
    hint: "Days remaining only",
    run: () => cloudOpsApi.triggerAlibabaCertificateExpiryScan(),
  },
] as const;

export function AlibabaScanActions({ onQueued }: { onQueued: () => void }) {
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function trigger(id: string, run: () => Promise<{ id: string; detail: string }>) {
    setBusy(id);
    setMessage(null);
    try {
      const result = await run();
      setMessage(`${result.detail}. Secret values were not requested.`);
      onQueued();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to queue the Alibaba job.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <CatalogPanel title="Alibaba inventory jobs" hint="Read-only discovery for China NonProd and Prod. PRD is scanned read-only. No destructive actions. AccessKey secrets are never sent to the browser.">
      <div className="flex flex-wrap gap-3 p-4">
        {ACTIONS.map((action) => (
          <button
            key={action.id}
            type="button"
            disabled={busy !== null}
            onClick={() => void trigger(action.id, action.run)}
            className="rounded border border-outline bg-white px-3 py-2 text-left text-xs font-semibold text-ink hover:bg-surface-low disabled:opacity-50"
          >
            <span className="block">{busy === action.id ? "Queuing…" : action.label}</span>
            <span className="block font-normal text-muted">{action.hint}</span>
          </button>
        ))}
      </div>
      {message ? <p className="border-t border-outline px-4 py-3 text-sm text-muted">{message}</p> : null}
    </CatalogPanel>
  );
}
