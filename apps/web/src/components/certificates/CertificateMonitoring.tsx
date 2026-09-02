"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CertificatesTable } from "@/components/certificates/CertificatesTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { isProductionEnvironment, regionsForProvider } from "@/lib/dashboard";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import { parseCertificatesFilters } from "@/lib/certificates";
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

export function CertificateMonitoring({
  initial,
}: {
  initial: ReturnType<typeof parseCertificatesFilters>;
}) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const provider = parseProvider(searchParams.get("provider") ?? "") ?? initial.provider ?? "all";
  const region = parseRegion(searchParams.get("region") ?? "") ?? initial.region ?? "all";
  const environment =
    parseEnvironment(searchParams.get("environment") ?? "") ?? initial.environment ?? "all";
  const selectedId = searchParams.get("certificate") || initial.certificate;

  const regions = regionsForProvider(provider === "all" ? "all" : provider);
  const scopedRegion = region !== "all" && !regions.includes(region) ? "all" : region;
  const state = useResource(
    (signal) =>
      cloudOpsApi.certificates(
        {
          provider,
          region: scopedRegion,
          environment,
        },
        signal,
      ),
    [provider, scopedRegion, environment],
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

  return (
    <>
      <PageHeader
        title="Certificate Monitoring"
        subtitle="TLS certificates across AWS EKS and Alibaba ACK. Private keys are never displayed."
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
      </div>
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <ProductionBanner environment={environment === "all" ? "all" : environment} />
          <QueryState
            state={state}
            loadingLabel="Loading certificates…"
            emptyLabel="No certificates in the current hierarchy filter."
            isEmpty={(data) => data.items.length === 0}
          >
            {() => (
              <>
                <section aria-label="Certificate summary" className="grid grid-cols-2 gap-4 md:grid-cols-5">
                  <Kpi label="Certificates in scope" value={summary.inScope} />
                  <Kpi
                    label="Expiring within 14d"
                    value={summary.expiring14d}
                    tone={summary.expiring14d > 0 ? "warning" : undefined}
                  />
                  <Kpi
                    label="Expired"
                    value={summary.expired}
                    tone={summary.expired > 0 ? "critical" : undefined}
                  />
                  <Kpi label="Auto-renew OK" value={summary.autoRenewOk} />
                  <Kpi label="PRD certificates" value={summary.prd} tone={summary.prd > 0 ? "prd" : undefined} />
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
}: {
  label: string;
  value: number;
  tone?: "warning" | "critical" | "prd";
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
  return (
    <article className={`rounded border border-outline bg-white p-3 ${bar}`}>
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
    </article>
  );
}
