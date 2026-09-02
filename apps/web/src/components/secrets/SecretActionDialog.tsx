import { useEffect, useState } from "react";
import { EnvBadge } from "@/components/status/EnvBadge";
import { cloudOpsApi } from "@/lib/api/client";
import { isProductionEnvironment } from "@/lib/dashboard";
import { isLiveCredential, SECRET_ACTION_LABELS, type SecretAction } from "@/lib/secrets";
import type { ManagedSecret } from "@/lib/secrets-data";

type HistoryRow = {
  at: string;
  actor: string;
  action: string;
  result: string;
  detail: string;
};

export function SecretActionDialog({
  secret,
  action,
  onClose,
  onConfirm,
}: {
  secret: ManagedSecret;
  action: SecretAction;
  onClose: () => void;
  onConfirm: (input: {
    secretValue?: string;
    confirmed: boolean;
    reason: string;
    changeTicket: string;
    rotationPolicyDays?: number;
  }) => Promise<void> | void;
}) {
  const production = isProductionEnvironment(secret.environment);
  const prd = secret.environment === "PRD";
  const mutating = action !== "history";
  const [acknowledged, setAcknowledged] = useState(false);
  const [reason, setReason] = useState("");
  const [changeTicket, setChangeTicket] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [rotationPolicyDays, setRotationPolicyDays] = useState("90");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryRow[]>(
    secret.history.map((event) => ({
      at: event.at,
      actor: event.actor,
      action: event.action,
      result: event.result,
      detail: event.detail,
    })),
  );

  useEffect(() => {
    if (action !== "history" || !isLiveCredential(secret.id)) {
      return;
    }
    const controller = new AbortController();
    cloudOpsApi
      .credentialHistory(secret.id, controller.signal)
      .then((payload) => {
        setHistory(
          payload.items.map((event) => ({
            at: event.createdAt,
            actor: event.actor,
            action: event.action,
            result: event.result,
            detail: event.detail,
          })),
        );
      })
      .catch(() => {
        // Keep catalog history if the live endpoint is unavailable.
      });
    return () => controller.abort();
  }, [action, secret.id]);

  const title =
    action === "history"
      ? "Rotation history"
      : prd
        ? `${SECRET_ACTION_LABELS[action]} production credential?`
        : production
          ? `${SECRET_ACTION_LABELS[action]} production credential?`
          : `${SECRET_ACTION_LABELS[action]} credential`;

  const confirmDisabled =
    busy ||
    ((prd || production) && mutating && (!acknowledged || !reason.trim())) ||
    (action === "replace" && !secretValue.trim());

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm({
        secretValue: action === "replace" ? secretValue : undefined,
        confirmed: acknowledged || !production,
        reason,
        changeTicket,
        rotationPolicyDays: action === "update" ? Number(rotationPolicyDays) || 90 : undefined,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed");
      setBusy(false);
      return;
    }
    setSecretValue("");
    setBusy(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button type="button" className="absolute inset-0 bg-black/40" aria-label="Close dialog" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="secret-action-title"
        className={
          prd && mutating
            ? "relative z-10 w-full max-w-lg rounded border-2 border-prd bg-white shadow-lg"
            : "relative z-10 w-full max-w-lg rounded border border-outline bg-white shadow-lg"
        }
      >
        {prd && mutating ? (
          <div className="bg-prd px-4 py-2 text-center text-[11px] font-bold uppercase tracking-wide text-white">
            Production environment
          </div>
        ) : null}
        <div className="space-y-4 p-5">
          <div>
            <h2 id="secret-action-title" className="text-lg font-semibold text-ink">
              {title}
            </h2>
            <p className="mt-2 font-mono text-xs text-muted">
              {secret.provider} → {secret.region} → {secret.account} → {secret.environment}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm font-semibold text-ink">{secret.name}</span>
              <span className="font-mono text-xs text-muted">{secret.credentialType || secret.namespace}</span>
              <EnvBadge environment={secret.environment} />
            </div>
          </div>

          {action === "history" ? (
            <ul className="divide-y divide-outline border border-outline">
              {history.length === 0 ? (
                <li className="p-3 text-sm text-muted">No rotation history recorded.</li>
              ) : (
                history.map((event) => (
                  <li key={`${event.at}-${event.action}-${event.actor}`} className="p-3">
                    <p className="text-sm font-semibold text-ink">
                      {event.action} · {event.result}
                    </p>
                    <p className="mt-0.5 text-xs text-muted">{event.detail}</p>
                    <p className="mt-1 font-mono text-[11px] text-muted">
                      {event.actor} · {event.at}
                    </p>
                  </li>
                ))
              )}
            </ul>
          ) : (
            <div className="space-y-3 text-sm text-ink">
              {prd ? (
                <p className="rounded border border-prd bg-prd/10 px-3 py-2 font-semibold text-prd">
                  WARNING: You are modifying a production credential.
                </p>
              ) : null}
              <p>
                {action === "update"
                  ? "Update writes metadata and rotation policy only. Secret values are never displayed or retrieved."
                  : action === "replace"
                    ? "The new value is sent to the secret backend over TLS and is not stored in PostgreSQL. The value cannot be retrieved later."
                    : "Validation queues a Celery identity check. Secret values are never returned."}
              </p>
              <p className="font-mono text-xs text-muted">
                Stored value: {secret.maskedValue || "••••••••••••"} (not retrievable)
              </p>
              {action === "replace" ? (
                <label className="block space-y-1">
                  <span className="text-[11px] font-bold uppercase tracking-wide text-muted">New secret value</span>
                  <textarea
                    className="h-24 w-full rounded border border-outline px-2 py-1 font-mono text-xs"
                    value={secretValue}
                    onChange={(event) => setSecretValue(event.target.value)}
                    autoComplete="off"
                    spellCheck={false}
                  />
                </label>
              ) : null}
              {action === "update" ? (
                <label className="block space-y-1">
                  <span className="text-[11px] font-bold uppercase tracking-wide text-muted">Rotation policy (days)</span>
                  <input
                    type="number"
                    min={1}
                    max={3650}
                    className="h-8 w-full rounded border border-outline px-2 text-sm"
                    value={rotationPolicyDays}
                    onChange={(event) => setRotationPolicyDays(event.target.value)}
                  />
                </label>
              ) : null}
              {production && mutating ? (
                <>
                  <label className="block space-y-1">
                    <span className="text-[11px] font-bold uppercase tracking-wide text-muted">Reason</span>
                    <input
                      className="h-8 w-full rounded border border-outline px-2 text-sm"
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-[11px] font-bold uppercase tracking-wide text-muted">Change ticket (optional)</span>
                    <input
                      className="h-8 w-full rounded border border-outline px-2 text-sm"
                      value={changeTicket}
                      onChange={(event) => setChangeTicket(event.target.value)}
                    />
                  </label>
                </>
              ) : null}
            </div>
          )}

          {prd && mutating ? (
            <label className="flex items-start gap-2 rounded border border-prd/40 bg-prd/5 p-3 text-sm text-ink">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={acknowledged}
                onChange={(event) => setAcknowledged(event.target.checked)}
              />
              <span>
                I understand this is a <span className="font-bold text-prd">PRD</span> production change.
                Secret values will not be shown and cannot be retrieved.
              </span>
            </label>
          ) : production && mutating ? (
            <label className="flex items-start gap-2 rounded border border-prd/30 bg-prd/5 p-3 text-sm text-ink">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={acknowledged}
                onChange={(event) => setAcknowledged(event.target.checked)}
              />
              <span>I understand this is a production change. Secret values are not retrievable.</span>
            </label>
          ) : null}

          {error ? <p className="text-sm text-prd">{error}</p> : null}

          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-3 py-1.5 text-xs font-semibold text-muted hover:text-ink">
              {action === "history" ? "Close" : "Cancel"}
            </button>
            {mutating ? (
              <button
                type="button"
                disabled={confirmDisabled}
                onClick={() => void submit()}
                className={
                  prd
                    ? "rounded bg-prd px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                    : "rounded bg-sidebar px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                }
              >
                {prd ? `${SECRET_ACTION_LABELS[action]} in production` : SECRET_ACTION_LABELS[action]}
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
