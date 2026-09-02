"use client";

import { cloudOpsApi } from "@/lib/api/client";
import { sourceLabel } from "@/lib/certificates";
import { useResource } from "@/lib/api/use-resource";
import type { CertificateRecord } from "@/lib/domain";

function Timeline({ daysRemaining, expiryStatus }: { daysRemaining: number; expiryStatus?: string }) {
  const clamped = Math.max(0, Math.min(90, daysRemaining));
  const percent = (clamped / 90) * 100;
  const tone =
    expiryStatus === "EXPIRED" || expiryStatus === "URGENT"
      ? "bg-critical"
      : expiryStatus === "CRITICAL" || expiryStatus === "WARNING"
        ? "bg-warning"
        : "bg-healthy";
  return (
    <div>
      <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted">Expiration timeline</p>
      <div className="h-2 rounded bg-surface-low">
        <div className={`h-2 rounded ${tone}`} style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-1 font-mono text-[11px] text-muted">
        {daysRemaining} days remaining · {expiryStatus || "UNKNOWN"}
      </p>
    </div>
  );
}

export function CertificateDetails({ certificateId }: { certificateId: string }) {
  const state = useResource(
    (signal) => cloudOpsApi.certificate(certificateId, signal),
    [certificateId],
  );
  if (state.status === "loading") {
    return <p className="p-4 text-sm text-muted">Loading certificate details…</p>;
  }
  if (state.status === "error") {
    return <p className="p-4 text-sm text-critical">{state.message}</p>;
  }
  const certificate: CertificateRecord = state.data;
  return (
    <section className="rounded border border-outline bg-white">
      <div className="border-b border-outline bg-surface-low px-4 py-3">
        <h2 className="text-[15px] font-semibold text-ink">{certificate.domain}</h2>
        <p className="mt-1 font-mono text-xs text-muted">
          {certificate.provider} → {certificate.region} → {certificate.account || "account"} → {certificate.environment}{" "}
          → {certificate.cluster} → {certificate.namespace}
        </p>
      </div>
      <div className="grid gap-4 p-4 md:grid-cols-2">
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Subject</dt>
            <dd className="font-mono text-xs">{certificate.domain}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">SANs</dt>
            <dd className="font-mono text-xs">{(certificate.subjectAlternativeNames || []).join(", ") || "—"}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Issuer</dt>
            <dd>{certificate.issuer}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Serial</dt>
            <dd className="font-mono text-xs">{certificate.serialNumber || "—"}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Validity</dt>
            <dd className="font-mono text-xs">
              {certificate.notBefore || "—"} → {certificate.notAfter || certificate.expiresOn}
            </dd>
          </div>
        </dl>
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Source</dt>
            <dd>{sourceLabel(certificate.source)}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Status</dt>
            <dd>{certificate.expiryStatus || certificate.renewalStatus}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">Auto-renew</dt>
            <dd>{certificate.autoRenew ? "Enabled / pending" : "Not reported"}</dd>
          </div>
          <div>
            <dt className="text-[11px] font-bold uppercase tracking-wide text-muted">In use by</dt>
            <dd className="font-mono text-xs">{(certificate.inUseBy || []).join(", ") || "—"}</dd>
          </div>
          <Timeline daysRemaining={certificate.daysRemaining} expiryStatus={certificate.expiryStatus} />
        </dl>
      </div>
      <div className="grid gap-4 border-t border-outline p-4 md:grid-cols-2">
        <div>
          <h3 className="mb-2 text-[13px] font-semibold text-ink">Discovery history</h3>
          {(certificate.history || []).length === 0 ? (
            <p className="text-sm text-muted">No discovery events recorded.</p>
          ) : (
            <ul className="space-y-2">
              {(certificate.history || []).map((event) => (
                <li key={event.id} className="font-mono text-xs text-muted">
                  {event.createdAt}: {event.event} {event.detail}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="mb-2 text-[13px] font-semibold text-ink">Alerts</h3>
          {(certificate.alerts || []).length === 0 ? (
            <p className="text-sm text-muted">No alerts for this certificate.</p>
          ) : (
            <ul className="space-y-2">
              {(certificate.alerts || []).map((alert) => (
                <li key={alert.id} className="text-sm">
                  {alert.kind} · {alert.severity} · {alert.status}
                </li>
              ))}
            </ul>
          )}
          <h3 className="mb-2 mt-4 text-[13px] font-semibold text-ink">Validation history</h3>
          {(certificate.validations || []).length === 0 ? (
            <p className="text-sm text-muted">No HTTPS validations recorded.</p>
          ) : (
            <ul className="space-y-2">
              {(certificate.validations || []).map((item) => (
                <li key={item.id} className="font-mono text-xs text-muted">
                  {item.checkedAt}: {item.hostname} {item.handshakeOk ? "ok" : "failed"} ({item.latencyMs}ms)
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <p className="border-t border-outline px-4 py-2 font-mono text-[11px] text-muted">
        Private keys are never stored or displayed.
      </p>
    </section>
  );
}
