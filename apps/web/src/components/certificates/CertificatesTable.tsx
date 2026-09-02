import { EnvBadge } from "@/components/status/EnvBadge";
import type { RenewalStatus } from "@/lib/certificates";
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
            <th className="p-3">Certificate</th>
            <th className="p-3">Domain</th>
            <th className="p-3">Provider</th>
            <th className="p-3">Region</th>
            <th className="p-3">Environment</th>
            <th className="p-3">Source</th>
            <th className="p-3">Issuer</th>
            <th className="p-3">Expiration date</th>
            <th className="p-3">Days remaining</th>
            <th className="p-3">Renewal status</th>
          </tr>
        </thead>
        <tbody>
          {certificates.map((certificate) => {
            const selected = certificate.id === selectedId;
            const expiring = certificate.renewalStatus === "Expiring";
            const expired = certificate.renewalStatus === "Expired";
            return (
              <tr
                key={certificate.id}
                className={
                  selected
                    ? "border-b border-outline bg-action/5 last:border-b-0"
                    : expiring
                      ? "border-b border-outline bg-warning/5 last:border-b-0"
                      : "border-b border-outline last:border-b-0"
                }
              >
                <td className="p-3 font-mono text-xs font-semibold text-ink">{certificate.name}</td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.domain}</td>
                <td className="p-3 text-muted">{certificate.provider}</td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.region}</td>
                <td className="p-3">
                  <EnvBadge environment={certificate.environment} />
                </td>
                <td className="p-3 text-xs text-muted">{certificate.source === "aws" ? "ACM live" : "Mock"}</td>
                <td className="p-3 text-muted">{certificate.issuer}</td>
                <td className="p-3 font-mono text-xs text-muted">{certificate.expiresOn}</td>
                <td
                  className={
                    expired
                      ? "p-3 font-semibold text-critical"
                      : expiring
                        ? "p-3 font-semibold text-warning"
                        : "p-3 text-muted"
                  }
                >
                  {certificate.daysRemaining}
                </td>
                <td className="p-3">
                  <RenewalChip status={certificate.renewalStatus} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
