"use client";

import { useState } from "react";
import { CatalogPanel } from "@/components/catalog/CatalogChrome";
import { cloudOpsApi } from "@/lib/api/client";

const ACTIONS = [
  {
    id: "discovery",
    label: "Discover EKS clusters",
    hint: "All AWS regions and accounts. PRD stays read-only.",
    run: () => cloudOpsApi.triggerClusterDiscovery(),
  },
  {
    id: "health",
    label: "Scan cluster health",
    hint: "Control plane and Kubernetes API",
    run: () => cloudOpsApi.triggerHealthScan(),
  },
  {
    id: "certs",
    label: "Scan ACM certificates",
    hint: "Expiry metadata only",
    run: () => cloudOpsApi.triggerCertificateScan(),
  },
] as const;

export function AwsScanActions({ onQueued }: { onQueued: () => void }) {
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
      setMessage(error instanceof Error ? error.message : "Unable to queue the AWS job.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <CatalogPanel title="AWS inventory jobs" hint="Read-only discovery across AMER, EMEA, and APAC. PRD is scanned read-only. No destructive actions. AWS secrets are never sent to the browser.">
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
