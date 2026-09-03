"use client";

import Link from "next/link";
import { useState } from "react";
import { cloudOpsApi } from "@/lib/api/client";
import type { EnvironmentIdentity } from "@/lib/domain";

export function EnvironmentActions({ identity }: { identity: EnvironmentIdentity }) {
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const environmentId = identity.id;

  async function run(action: "refresh" | "discover" | "certificates" | "health") {
    if (!environmentId) {
      setMessage("Configure this environment in Administration before running scans.");
      return;
    }
    setBusy(action);
    setMessage("");
    try {
      if (action === "discover" || action === "refresh") {
        const result = await cloudOpsApi.discoverEnvironment(environmentId);
        setMessage(`Cluster discovery started. Job ${result.jobId}`);
      } else if (action === "certificates") {
        const result = await cloudOpsApi.environmentCertificateScan(environmentId);
        setMessage(`Certificate scan started. Job ${result.jobId}`);
      } else {
        const result = await cloudOpsApi.environmentHealthScan(environmentId);
        setMessage(`Health check started. Job ${result.jobId}`);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Action failed");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="rounded border border-outline bg-white p-4">
      <div className="flex flex-wrap gap-2">
        <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs font-semibold" disabled={!!busy} onClick={() => void run("refresh")}>
          {busy === "refresh" ? "Starting…" : "Refresh"}
        </button>
        <button type="button" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white" disabled={!!busy} onClick={() => void run("discover")}>
          {busy === "discover" ? "Starting…" : "Discover Clusters"}
        </button>
        <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs font-semibold" disabled={!!busy} onClick={() => void run("certificates")}>
          {busy === "certificates" ? "Starting…" : "Scan Certificates"}
        </button>
        <button type="button" className="rounded border border-outline px-3 py-1.5 text-xs font-semibold" disabled={!!busy} onClick={() => void run("health")}>
          {busy === "health" ? "Starting…" : "Run Health Check"}
        </button>
        <Link href="/administration?section=environments" className="rounded border border-outline px-3 py-1.5 text-xs font-semibold">
          Edit in Administration
        </Link>
      </div>
      {identity.readiness ? <p className="mt-2 text-xs text-muted">Readiness {identity.readiness}</p> : null}
      {message ? <p className="mt-2 text-sm text-ink">{message}</p> : null}
    </div>
  );
}
