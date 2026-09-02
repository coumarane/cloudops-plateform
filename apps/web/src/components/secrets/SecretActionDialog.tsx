import { useState } from "react";
import { EnvBadge } from "@/components/status/EnvBadge";
import { isProductionEnvironment } from "@/lib/dashboard";
import { SECRET_ACTION_LABELS, type SecretAction } from "@/lib/secrets";
import type { ManagedSecret } from "@/lib/secrets-data";

export function SecretActionDialog({
  secret,
  action,
  onClose,
  onConfirm,
}: {
  secret: ManagedSecret;
  action: SecretAction;
  onClose: () => void;
  onConfirm: (secret: ManagedSecret, action: Exclude<SecretAction, "history">) => void;
}) {
  const production = isProductionEnvironment(secret.environment);
  const prd = secret.environment === "PRD";
  const mutating = action !== "history";
  const [acknowledged, setAcknowledged] = useState(false);

  const title =
    action === "history"
      ? "Rotation history"
      : prd
        ? `${SECRET_ACTION_LABELS[action]} secret in PRD?`
        : production
          ? `${SECRET_ACTION_LABELS[action]} secret in production?`
          : `${SECRET_ACTION_LABELS[action]} secret`;

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
              <span className="font-mono text-xs text-muted">{secret.namespace}</span>
              <EnvBadge environment={secret.environment} />
            </div>
          </div>

          {action === "history" ? (
            <ul className="divide-y divide-outline border border-outline">
              {secret.history.map((event) => (
                <li key={`${event.at}-${event.action}`} className="p-3">
                  <p className="text-sm font-semibold text-ink">
                    {event.action} · {event.result}
                  </p>
                  <p className="mt-0.5 text-xs text-muted">{event.detail}</p>
                  <p className="mt-1 font-mono text-[11px] text-muted">
                    {event.actor} · {event.at}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink">
              {action === "update"
                ? "Update writes metadata and rotation policy to the vault. This console does not accept or display secret values."
                : action === "rotate"
                  ? "Rotation is performed in the vault. This console will not display the secret value before or after rotation."
                  : "Validation checks vault health and checksums only. Secret values are never retrieved."}
            </p>
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
                Secret values will not be shown.
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
              <span>I understand this is a production change. Secret values will not be shown.</span>
            </label>
          ) : null}

          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-3 py-1.5 text-xs font-semibold text-muted hover:text-ink">
              {action === "history" ? "Close" : "Cancel"}
            </button>
            {mutating ? (
              <button
                type="button"
                disabled={(prd || production) && !acknowledged}
                onClick={() => onConfirm(secret, action)}
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
