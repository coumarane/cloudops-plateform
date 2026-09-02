import Link from "next/link";
import { EnvBadge } from "@/components/status/EnvBadge";
import { certificatesHref, sourceLabel, type RenewalStatus } from "@/lib/certificates";
import type { ManagedCertificate } from "@/lib/certificates-data";

function RenewalChip({ status }: { status: RenewalStatus }) {
  if (status === "Expired") {
    return (
      <span className="rounded bg-critical px-2 py-0.5 text-xs font-semibold text-white">Expired</span>
    );
  }
  if (status === "Expiring") {
    return (
      <span className="rounded bg-warning/10 px-2 py-0.5 text-xs font-semibold text-warning">
        Expiring
      </span>
    );
  }
  if (status === "Renewing") {
    return (
      <span className="rounded bg-action/10 px-2 py-0.5 text-xs font-semibold text-action">
        Renewing
      </span>
    );
  }
  return <span className="rounded bg-healthy/10 px-2 py-0.5 text-xs font-semibold text-healthy">OK</span>;
}

function ExpiryChip({ status }: { status?: string }) {
  const value = (status || "").toUpperCase();
  if (value === "EXPIRED" || value === "URGENT") {
    return <span className="rounded bg-critical px-2 py-0.5 text-xs font-semibold text-white">{value || "UNKNOWN"}</span>;
  }
  if (value === "CRITICAL" || value === "WARNING") {
    return (
      <span className="rounded bg-warning/10 px-2 py-0.5 text-xs font-semibold text-warning">{value}</span>
    );
  }
  if (value === "HEALTHY") {
    return <span className="rounded bg-healthy/10 px-2 py-0.5 text-xs font-semibold text-healthy">HEALTHY</span>;
  }
  return <span className="text-xs text-muted">{value || "UNKNOWN"}</span>;
}

export function CertificatesTable({
  certificates,
  selectedId,
}: {
  certificates: ManagedCertificate[];
  selectedId?: string | null;
}) {
  if (certificates.length === 0) {
    return <p className="p-4 text-sm text-muted">No certificates in the current hierarchy filter.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-outline text-[11px] font-bold uppercase tracking-wide text-muted">
            <th className="p-3">Certificate / domain</th>
            <th className="p-3">Provider</th>
            <th className="p-3">Region</th>
            <th className="p-3">Account</th>
            <th className="p-3">Environment</th>
            <th className="p-3">Cluster</th>
            <th className="p-3">Namespace</th>
            <th className="p-3">Source</th>
            <th className="p-3">Issuer</th>
            <th className="p-3">Expiration</th>
            <th className="p-3">Days remaining</th>
            <th className="p-3">Renewal</th>
            <th className="p-3">Alert</th>
            <th className="p-3">Last checked</th>
          </tr>
        </thead>
        <tbody>
          {certificates.map((certificate) => {
            const selected = certificate.id === selectedId;
            const expired = certificate.expiryStatus === "EXPIRED" || certificate.renewalStatus === "Expired";
            const urgent = certificate.expiryStatus === "URGENT" || certificate.expiryStatus === "CRITICAL";
            return (
              <tr
                key={certificate.id}
                className={
                  selected
                    ? "border-b border-outline bg-action/5 last:border-b-0"
                    : expired || urgent
                      ? "border-b border-outline bg-warning/5 last:border-b-0"
                      : "border-b border-outline last:border-b-0"
                }
              >
                <td className="p-3">
                  <Link
                    href={certificatesHref({
                      provider: certificate.provider,
                      region: certificate.region,
                      environment: certificate.environment,
                      certificate: certificate.id,
                    })}
                    className="font-mono text-xs font-semibold text-action hover:underline"
                  >
                    {certificate.domain}
                  </Link>
                  <p className="mt-0.5 font-mono text-[11px] text-muted">{certificate.name}</p>
                </td>
                <td className="p-3 text-muted">{certificate.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.region}</td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.account || "—"}</td>
                <td className="p-3">
                  <EnvBadge environment={certificate.environment} />
                </td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.cluster}</td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.namespace}</td>
                <td className="p-3 text-xs text-muted">{sourceLabel(certificate.source)}</td>
                <td className="p-3 text-muted">{certificate.issuer}</td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.expiresOn}</td>
                <td
                  className={
                    expired
                      ? "p-3 font-semibold text-critical"
                      : urgent
                        ? "p-3 font-semibold text-warning"
                        : "p-3 text-muted"
                  }
                >
                  {certificate.daysRemaining}
                </td>
                <td className="p-3">
                  <RenewalChip status={certificate.renewalStatus} />
                </td>
                <td className="p-3">
                  <ExpiryChip status={certificate.expiryStatus} />
                  {certificate.alertStatus ? (
                    <p className="mt-1 text-[10px] uppercase tracking-wide text-muted">{certificate.alertStatus}</p>
                  ) : null}
                </td>
                <td className="p-3 font-mono text-[11px] text-muted">{certificate.lastChecked || "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
