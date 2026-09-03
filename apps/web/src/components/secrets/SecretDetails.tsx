"use client";

import { useState } from "react";
import { EnvBadge } from "@/components/status/EnvBadge";
import { cloudOpsApi } from "@/lib/api/client";
import type { ManagedSecret } from "@/lib/secrets-data";

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    if (!value || value === "—") return;
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div>
      <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1 flex items-start gap-2">
        <span className="break-all font-mono text-xs text-ink">{value || "—"}</span>
        {value && value !== "—" ? (
          <button
            type="button"
            onClick={() => void copy()}
            className="shrink-0 text-[11px] font-semibold text-action hover:underline"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        ) : null}
      </dd>
    </div>
  );
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M3 3l18 18" />
      <path d="M10.6 10.6A2 2 0 0012 14a2 2 0 001.4-.6M9.9 5.1A10.5 10.5 0 0121 12c-.6 1-1.4 2-2.3 2.8M6.1 6.1C4.6 7.3 3.4 8.7 3 12c1.5 3.8 5.1 6.5 9 6.5 1.2 0 2.3-.2 3.4-.7" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function SecretDetails({
  secret,
  onBack,
  onAction,
}: {
  secret: ManagedSecret;
  onBack: () => void;
  onAction: (action: "update" | "replace" | "validate" | "history") => void;
}) {
  const [tab, setTab] = useState<"overview" | "rotation">("overview");
  const [view, setView] = useState<"pairs" | "plaintext">("pairs");
  const keys = secret.keys ?? [];
  const [pairs, setPairs] = useState<Record<string, string> | null>(null);
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function retrieve() {
    setLoading(true);
    setError("");
    try {
      const response = await cloudOpsApi.revealSecret(secret.arn || secret.id, secret.environment);
      const next: Record<string, string> = {};
      for (const item of response.items) next[item.name] = item.revealed;
      setPairs(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to retrieve secret value");
    } finally {
      setLoading(false);
    }
  }

  function toggle(key: string) {
    if (!pairs) {
      void retrieve().then(() => setVisible((current) => ({ ...current, [key]: true })));
      return;
    }
    setVisible((current) => ({ ...current, [key]: !current[key] }));
  }

  const displayKeys = pairs ? Object.keys(pairs) : keys;

  return (
    <div className="space-y-4">
      <nav className="flex items-center gap-2 text-xs text-muted">
        <button type="button" onClick={onBack} className="font-semibold text-action hover:underline">
          Secrets
        </button>
        <span aria-hidden="true">/</span>
        <span className="font-mono text-ink">{secret.name}</span>
      </nav>

      <section className="rounded border border-outline bg-white">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-outline bg-surface-low px-5 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">AWS Secrets Manager</p>
            <h2 className="mt-1 text-xl font-semibold text-ink">{secret.name}</h2>
            <p className="mt-1 text-xs text-muted">
              {secret.provider} → {secret.region} → {secret.account} → {secret.environment}
              {secret.cloudRegion ? ` · ${secret.cloudRegion}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <EnvBadge environment={secret.environment} />
            <span className="rounded bg-healthy/10 px-2 py-0.5 text-xs font-semibold text-healthy">Healthy</span>
            <button
              type="button"
              onClick={() => onAction("validate")}
              className="rounded border border-outline bg-white px-3 py-1.5 text-xs font-semibold text-ink hover:bg-surface-low"
            >
              Validate
            </button>
          </div>
        </div>
        <dl className="grid gap-4 p-5 md:grid-cols-2">
          <CopyField label="Encryption key" value={secret.kmsKeyId || "aws/secretsmanager"} />
          <CopyField label="Secret name" value={secret.name} />
          <CopyField label="Secret ARN" value={secret.arn || secret.id} />
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Description</dt>
            <dd className="mt-1 text-sm text-ink">{secret.description || "—"}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Account</dt>
            <dd className="mt-1 font-mono text-xs text-ink">{secret.account}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Secret type</dt>
            <dd className="mt-1 font-mono text-xs text-ink">{secret.credentialType || secret.namespace}</dd>
          </div>
        </dl>
      </section>

      <div className="flex border-b border-outline">
        {(
          [
            ["overview", "Overview"],
            ["rotation", "Rotation"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={
              tab === id
                ? "border-b-2 border-action px-4 py-2 text-sm font-semibold text-action"
                : "px-4 py-2 text-sm font-semibold text-muted hover:text-ink"
            }
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" ? (
        <section className="rounded border border-outline bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-outline px-5 py-3">
            <div>
              <h3 className="text-[15px] font-semibold text-ink">Secret value</h3>
              <p className="mt-0.5 text-xs text-muted">Values stay masked until you retrieve them with the eye icon.</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void retrieve()}
                disabled={loading}
                className="rounded border border-outline bg-white px-3 py-1.5 text-xs font-semibold text-ink hover:bg-surface-low disabled:opacity-40"
              >
                {loading ? "Retrieving…" : pairs ? "Refresh value" : "Retrieve secret value"}
              </button>
              <div className="flex rounded border border-outline">
                <button
                  type="button"
                  onClick={() => setView("pairs")}
                  className={`px-3 py-1.5 text-xs font-semibold ${view === "pairs" ? "bg-surface-low text-ink" : "text-muted"}`}
                >
                  Key/value
                </button>
                <button
                  type="button"
                  onClick={() => setView("plaintext")}
                  className={`border-l border-outline px-3 py-1.5 text-xs font-semibold ${view === "plaintext" ? "bg-surface-low text-ink" : "text-muted"}`}
                >
                  Plaintext
                </button>
              </div>
            </div>
          </div>
          {error ? <p className="border-b border-outline px-5 py-2 text-sm text-critical">{error}</p> : null}
          {displayKeys.length === 0 ? (
            <p className="p-5 text-sm text-muted">No JSON keys were found for this secret.</p>
          ) : view === "pairs" ? (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
                  <th className="px-5 py-2">Secret key</th>
                  <th className="px-5 py-2">Secret value</th>
                </tr>
              </thead>
              <tbody>
                {displayKeys.map((key) => {
                  const shown = Boolean(visible[key] && pairs?.[key] !== undefined);
                  return (
                    <tr key={key} className="border-b border-outline last:border-b-0">
                      <td className="px-5 py-3 font-mono text-xs font-semibold text-ink">{key}</td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-ink">
                            {shown ? pairs?.[key] : secret.maskedValue || "••••••••••••"}
                          </span>
                          <button
                            type="button"
                            aria-label={shown ? `Hide ${key}` : `Show ${key}`}
                            onClick={() => toggle(key)}
                            className="rounded p-1 text-muted hover:bg-surface-low hover:text-ink"
                          >
                            <EyeIcon open={shown} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <pre className="overflow-x-auto p-5 font-mono text-xs text-ink">
              {`{\n${displayKeys
                .map((key) => `  "${key}": "${visible[key] && pairs?.[key] !== undefined ? pairs[key] : "••••••••••••"}"`)
                .join(",\n")}\n}`}
            </pre>
          )}
        </section>
      ) : (
        <section className="rounded border border-outline bg-white p-5">
          <dl className="grid gap-4 md:grid-cols-3">
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Last rotated</dt>
              <dd className="mt-1 font-mono text-xs text-ink">{secret.lastRotated}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Rotation due</dt>
              <dd className="mt-1 font-mono text-xs text-ink">{secret.nextDue}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Last validated</dt>
              <dd className="mt-1 font-mono text-xs text-ink">{secret.lastValidated}</dd>
            </div>
          </dl>
        </section>
      )}
    </div>
  );
}
