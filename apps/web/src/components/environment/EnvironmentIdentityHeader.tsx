import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { EnvBadge } from "@/components/status/EnvBadge";
import { isProductionEnvironment } from "@/lib/dashboard";
import { environmentTitle, type EnvironmentIdentity } from "@/lib/environment-data";

export function EnvironmentIdentityHeader({ identity }: { identity: EnvironmentIdentity }) {
  const production = isProductionEnvironment(identity.environment);
  const title = environmentTitle(identity);

  return (
    <div
      className={
        production
          ? "border-b border-prd/30 border-l-4 border-l-prd bg-white px-6 py-6"
          : "border-b border-outline bg-white px-6 py-6"
      }
    >
      <nav aria-label="Breadcrumb" className="mb-2 flex flex-wrap items-center gap-2 text-[13px] text-muted">
        <Link href="/environments" className="hover:text-ink">
          Environments
        </Link>
        <ChevronRight className="h-4 w-4" aria-hidden />
        <span>{identity.provider}</span>
        <ChevronRight className="h-4 w-4" aria-hidden />
        <span>{identity.region}</span>
        <ChevronRight className="h-4 w-4" aria-hidden />
        <span className="font-medium text-ink">{identity.environment}</span>
      </nav>
      <h1 className="mb-3 text-2xl font-semibold tracking-tight text-ink">{title}</h1>
      <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-muted">
        <span className="rounded border border-outline bg-surface-low px-2 py-1 text-ink">
          {identity.provider} ({identity.platform})
        </span>
        <span aria-hidden>•</span>
        <span>{identity.region}</span>
        <span aria-hidden>•</span>
        <span>{identity.cloudRegion}</span>
        <span aria-hidden>•</span>
        <EnvBadge environment={identity.environment} />
        <span aria-hidden>•</span>
        <span
          className={
            production
              ? "rounded bg-prd px-2 py-1 text-[11px] font-bold uppercase tracking-wide text-white"
              : "text-[11px] font-bold uppercase tracking-wide text-ink"
          }
        >
          {production ? "PRODUCTION" : "NON-PRODUCTION"}
        </span>
        <span aria-hidden>•</span>
        <span className="text-ink">account: {identity.account}</span>
        {identity.readonly ? (
          <>
            <span aria-hidden>•</span>
            <span className="rounded bg-prd/10 px-2 py-1 text-[11px] font-bold uppercase tracking-wide text-prd">
              Read-only
            </span>
          </>
        ) : null}
        {identity.discoveryActive ? (
          <>
            <span aria-hidden>•</span>
            <span className="rounded bg-healthy/10 px-2 py-1 text-[11px] font-bold uppercase tracking-wide text-healthy">
              {identity.provider} live
            </span>
          </>
        ) : null}
      </div>
      {identity.lastError ? (
        <p className="mt-3 font-mono text-xs text-warning">Last scan error: {identity.lastError}</p>
      ) : null}
      {identity.lastSuccessfulScan ? (
        <p className="mt-2 font-mono text-xs text-muted">Last successful scan: {identity.lastSuccessfulScan}</p>
      ) : null}
    </div>
  );
}
