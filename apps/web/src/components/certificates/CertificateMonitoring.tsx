"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CertificateDetails } from "@/components/certificates/CertificateDetails";
import { CertificatesTable } from "@/components/certificates/CertificatesTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { isProductionEnvironment, regionsForProvider } from "@/lib/dashboard";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import { certificatesHref, parseCertificatesFilters } from "@/lib/certificates";
import { summarizeCertificates } from "@/lib/certificates-data";
import {
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  providerToSlug,
  regionToSlug,
} from "@/lib/environment";
import { ENVIRONMENTS, type Environment } from "@/lib/types";
import Link from "next/link";
import { useState } from "react";

export function CertificateMonitoring({
  initial,
}: {
  initial: ReturnType<typeof parseCertificatesFilters>;
}) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const provider = parseProvider(searchParams.get("provider") ?? "") ?? initial.provider ?? "all";
  const region = parseRegion(searchParams.get("region") ?? "") ?? initial.region ?? "all";
  const environment =
    parseEnvironment(searchParams.get("environment") ?? "") ?? initial.environment ?? "all";
  const selectedId = searchParams.get("certificate") || initial.certificate;
  const status = searchParams.get("status") || initial.status;
  const expiresWithinDays = searchParams.get("expires_within_days") || (initial.expiresWithinDays ? String(initial.expiresWithinDays) : null);
  const sort = searchParams.get("sort") || initial.sort || "days_remaining";

  const regions = regionsForProvider(provider === "all" ? "all" : provider);
  const scopedRegion = region !== "all" && !regions.includes(region) ? "all" : region;
  const state = useResource(
    (signal) =>
      cloudOpsApi.certificates(
        {
          provider,
          region: scopedRegion,
          environment,
          status,
          expiresWithinDays,
          sort,
        },
        signal,
      ),
    [provider, scopedRegion, environment, status, expiresWithinDays, sort],
  );
  const certificates = state.status === "success" ? state.data.items : [];
  const summary = summarizeCertificates(certificates);

  function setFilter(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (!value || value === "all") params.delete(key);
      else params.set(key, value);
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  async function triggerScan() {
    try {
      const job = await cloudOpsApi.triggerCertificateDiscovery();
      setScanMessage(`Scan queued (${job.kind || "certificate-discovery"})`);
    } catch (error) {
      setScanMessage(error instanceof Error ? error.message : "Scan failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Certificate Monitoring"
        subtitle="TLS certificates across AWS ACM/EKS and Alibaba CAS/ACK. Private keys are never displayed."
        meta={state.status === "success" ? `Last synced: ${state.data.lastSynced}` : "Last synced: —"}
      />
      <div className="flex flex-wrap items-center gap-4 border-b border-outline bg-canvas px-6 py-2 text-[11px] font-bold uppercase tracking-wide text-muted">
        <span>Hierarchy:</span>
        <label className="flex items-center gap-2">
          Provider:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={provider === "all" ? "all" : providerToSlug(provider)}
            onChange={(event) =>
              setFilter({
                provider: event.target.value,
                region: null,
              })
            }
          >
            <option value="all">All providers</option>
            <option value="aws">AWS</option>
            <option value="alibaba">Alibaba</option>
          </select>
        </label>
        <label className="flex items-center gap-2">
          Region:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={scopedRegion === "all" ? "all" : regionToSlug(scopedRegion)}
            onChange={(event) => setFilter({ region: event.target.value })}
          >
            <option value="all">All regions</option>
            {regions.map((item) => (
              <option key={item} value={regionToSlug(item)}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          Environment:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={environment === "all" ? "all" : environmentToSlug(environment)}
            onChange={(event) => setFilter({ environment: event.target.value })}
          >
            <option value="all">All environments</option>
            {ENVIRONMENTS.map((item) => (
              <option key={item} value={environmentToSlug(item)}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          Status:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={status || "all"}
            onChange={(event) =>
              setFilter({
                status: event.target.value === "all" ? null : event.target.value,
                expires_within_days: null,
              })
            }
          >
            <option value="all">All</option>
            <option value="healthy">Healthy</option>
            <option value="warning">Warning (31–60d)</option>
            <option value="critical">Critical (8–30d)</option>
            <option value="urgent">Urgent (1–7d)</option>
            <option value="expired">Expired</option>
          </select>
        </label>
        <label className="flex items-center gap-2">
          Window:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={expiresWithinDays || "all"}
            onChange={(event) =>
              setFilter({
                expires_within_days: event.target.value === "all" ? null : event.target.value,
                status: null,
              })
            }
          >
            <option value="all">Any</option>
            <option value="7">&lt; 7 days</option>
            <option value="30">&lt; 30 days</option>
            <option value="60">&lt; 60 days</option>
          </select>
        </label>
        <label className="flex items-center gap-2">
          Sort:
          <select
            className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
            value={sort}
            onChange={(event) => setFilter({ sort: event.target.value })}
          >
            <option value="days_remaining">Days remaining</option>
            <option value="expires_at">Expiration date</option>
            <option value="environment">Environment</option>
            <option value="severity">Severity</option>
          </select>
        </label>
        <button
          type="button"
          className="ml-auto h-6 rounded bg-action px-3 text-[11px] font-bold uppercase tracking-wide text-white"
          onClick={() => void triggerScan()}
        >
          Scan certificates
        </button>
      </div>
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <ProductionBanner environment={environment === "all" ? "all" : environment} />
          {scanMessage ? <p className="text-sm text-ink">{scanMessage}</p> : null}
          <QueryState
            state={state}
            loadingLabel="Loading certificates…"
            emptyLabel="No certificates discovered."
            isEmpty={(data) => data.items.length === 0}
            emptyAction={
              <Link href="/administration?section=environments" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
                Scan Certificates
              </Link>
            }
          >
            {() => (
              <>
                <section aria-label="Certificate summary" className="grid grid-cols-2 gap-4 md:grid-cols-5">
                  <Kpi href={certificatesHref({ status: "healthy" })} label="Healthy" value={summary.healthy} />
                  <Kpi
                    href="/certificates?expires_within_days=60"
                    label="Expiring &lt; 60 days"
                    value={summary.expiring60}
                    tone={summary.expiring60 > 0 ? "warning" : undefined}
                  />
                  <Kpi
                    href="/certificates?expires_within_days=30"
                    label="Expiring &lt; 30 days"
                    value={summary.expiring30}
                    tone={summary.expiring30 > 0 ? "warning" : undefined}
                  />
                  <Kpi
                    href="/certificates?expires_within_days=7"
                    label="Expiring &lt; 7 days"
                    value={summary.expiring7}
                    tone={summary.expiring7 > 0 ? "critical" : undefined}
                  />
                  <Kpi
                    href={certificatesHref({ status: "expired" })}
                    label="Expired"
                    value={summary.expired}
                    tone={summary.expired > 0 ? "critical" : undefined}
                  />
                </section>
                <section className="rounded border border-outline bg-white">
                  <div className="border-b border-outline bg-surface-low px-4 py-3">
                    <h2 className="text-[15px] font-semibold text-ink">Certificate catalog</h2>
                    <p className="mt-1 text-xs text-muted">
                      Public TLS metadata only. Private keys are never displayed.
                    </p>
                  </div>
                  <CertificatesTable certificates={certificates} selectedId={selectedId} />
                </section>
                {selectedId ? <CertificateDetails certificateId={selectedId} /> : null}
              </>
            )}
          </QueryState>
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Private keys are never displayed in this console.
          </p>
        </div>
      </main>
    </>
  );
}

function ProductionBanner({ environment }: { environment: Environment | "all" }) {
  if (environment === "all" || !isProductionEnvironment(environment)) {
    return null;
  }

  const prd = environment === "PRD";
  return (
    <div className="space-y-4">
      {prd ? (
        <div className="border-y-4 border-prd bg-prd px-4 py-1 text-center text-[11px] font-bold uppercase tracking-wide text-white">
          Production environment
        </div>
      ) : null}
      <div
        role="alert"
        className={prd ? "border border-prd bg-prd/10 px-4 py-3" : "border border-prd/40 bg-prd/5 px-4 py-3"}
      >
        <p className="text-[11px] font-bold uppercase tracking-wide text-prd">
          {prd ? "Production environment — PRD" : "Production environment"}
        </p>
        <p className="mt-1 text-sm text-ink">
          Certificates in {prd ? "PRD" : environment} are high-risk. Expiration and renewal metadata
          only. Private keys are never displayed.
        </p>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  tone,
  href,
}: {
  label: string;
  value: number;
  tone?: "warning" | "critical" | "prd";
  href?: string;
}) {
  const bar =
    tone === "prd"
      ? "border-l-4 border-l-prd"
      : tone === "warning"
        ? "border-l-4 border-l-warning"
        : tone === "critical"
          ? "border-l-4 border-l-critical"
          : "border-l-4 border-l-outline";
  const valueClass =
    tone === "prd"
      ? "text-prd"
      : tone === "warning"
        ? "text-warning"
        : tone === "critical"
          ? "text-critical"
          : "text-ink";
  const body = (
    <article className={`rounded border border-outline bg-white p-3 ${bar}`}>
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
    </article>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}
