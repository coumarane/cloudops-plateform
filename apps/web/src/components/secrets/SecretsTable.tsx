import { EnvBadge } from "@/components/status/EnvBadge";
import { SECRET_ACTION_LABELS, type SecretAction } from "@/lib/secrets";
import type { ManagedSecret } from "@/lib/secrets-data";

function StatusChip({ status, lifecycle }: { status: ManagedSecret["status"]; lifecycle?: string | null }) {
  if (lifecycle === "INVALID") {
    return <span className="rounded bg-warning/10 px-2 py-0.5 text-xs font-semibold text-warning">Invalid</span>;
  }
  if (lifecycle === "DISABLED") {
    return <span className="rounded bg-surface-low px-2 py-0.5 text-xs font-semibold text-muted">Disabled</span>;
  }
  if (status === "Overdue" || lifecycle === "OVERDUE") {
    return <span className="rounded bg-warning/10 px-2 py-0.5 text-xs font-semibold text-warning">Overdue</span>;
  }
  if (status === "Due soon" || lifecycle === "ROTATION_DUE") {
    return <span className="rounded bg-warning/10 px-2 py-0.5 text-xs font-semibold text-warning">Due soon</span>;
  }
  return <span className="rounded bg-healthy/10 px-2 py-0.5 text-xs font-semibold text-healthy">Healthy</span>;
}

export function SecretsTable({
  secrets,
  onAction,
}: {
  secrets: ManagedSecret[];
  onAction: (secret: ManagedSecret, action: SecretAction) => void;
}) {
  if (secrets.length === 0) {
    return <p className="p-4 text-sm text-muted">No secrets in the current hierarchy filter.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Credential name</th>
            <th className="p-3">Type</th>
            <th className="p-3">Provider</th>
            <th className="p-3">Region</th>
            <th className="p-3">Account</th>
            <th className="p-3">Environment</th>
            <th className="p-3">Value</th>
            <th className="p-3">Fingerprint</th>
            <th className="p-3">Status</th>
            <th className="p-3">Last rotated</th>
            <th className="p-3">Rotation due</th>
            <th className="p-3">Last validated</th>
            <th className="p-3">Updated by</th>
            <th className="p-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {secrets.map((secret) => (
            <tr key={secret.id} className="border-b border-outline last:border-b-0">
              <td className="p-3 font-mono text-xs font-semibold text-ink">{secret.name}</td>
              <td className="p-3 font-mono text-xs text-muted">{secret.credentialType || secret.namespace}</td>
              <td className="p-3 text-muted">{secret.provider}</td>
              <td className="p-3 font-mono text-xs text-muted">{secret.region}</td>
              <td className="p-3 font-mono text-xs text-muted">{secret.account}</td>
              <td className="p-3">
                <EnvBadge environment={secret.environment} />
              </td>
              <td className="p-3 font-mono text-xs text-muted" title="Secret values are not retrievable from this console">
                {secret.maskedValue || "••••••••••••"}
              </td>
              <td className="p-3 font-mono text-xs text-muted">{secret.fingerprint || "—"}</td>
              <td className="p-3">
                <StatusChip status={secret.status} lifecycle={secret.lifecycleStatus} />
              </td>
              <td className="p-3 text-muted">{secret.lastRotated}</td>
              <td className="p-3 text-muted">{secret.nextDue}</td>
              <td className="p-3 text-muted">{secret.lastValidated}</td>
              <td className="p-3 font-mono text-xs text-muted">{secret.updatedBy || "—"}</td>
              <td className="p-3">
                <div className="flex flex-wrap justify-end gap-2">
                  {(["update", "replace", "validate", "history"] as const).map((action) => (
                    <button
                      key={action}
                      type="button"
                      onClick={() => onAction(secret, action)}
                      className={
                        action === "replace" && secret.environment === "PRD"
                          ? "text-xs font-semibold text-prd hover:underline"
                          : "text-xs font-semibold text-action hover:underline"
                      }
                    >
                      {SECRET_ACTION_LABELS[action]}
                    </button>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
