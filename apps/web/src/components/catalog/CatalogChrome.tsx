import { isProductionEnvironment } from "@/lib/dashboard";
import type { Environment } from "@/lib/types";
import { PageHeader } from "@/components/layout/PageHeader";
import type { ReactNode } from "react";

export function CatalogBody({
  title,
  subtitle,
  environment,
  banner,
  kpis,
  filters,
  children,
  lastSynced,
}: {
  title: string;
  subtitle: string;
  environment: Environment | "all";
  banner: string;
  kpis: ReactNode;
  filters: ReactNode;
  children: ReactNode;
  lastSynced?: string;
}) {
  return (
    <>
      <PageHeader
        title={title}
        subtitle={subtitle}
        meta={lastSynced ? `Last synced: ${lastSynced}` : "Last synced: —"}
      />
      {filters}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <ProductionScopeBanner environment={environment} message={banner} />
          {kpis}
          {children}
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Secret values are never displayed in this console.
          </p>
        </div>
      </main>
    </>
  );
}

export function ProductionScopeBanner({
  environment,
  message,
}: {
  environment: Environment | "all";
  message: string;
}) {
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
        <p className="mt-1 text-sm text-ink">{message}</p>
      </div>
    </div>
  );
}

export function KpiGrid({ children }: { children: ReactNode }) {
  return (
    <section aria-label="Summary" className="grid grid-cols-2 gap-4 md:grid-cols-5">
      {children}
    </section>
  );
}

export function Kpi({
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

export function CatalogPanel({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded border border-outline bg-white">
      <div className="border-b border-outline bg-surface-low px-4 py-3">
        <h2 className="text-[15px] font-semibold text-ink">{title}</h2>
        {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
      </div>
      {children}
    </section>
  );
}

export function StatusChip({
  value,
}: {
  value: string;
}) {
  const tone = chipTone(value);
  return <span className={tone}>{value}</span>;
}

function chipTone(value: string): string {
  const base = "rounded px-2 py-0.5 text-xs font-semibold";
  const key = value.toLowerCase();
  if (key === "medium" || key === "low") {
    return `${base} bg-action/10 text-action`;
  }
  if (key === "unreachable" || key === "failed" || key === "failing" || key === "critical" || key === "unhealthy") {
    return `${base} bg-critical px-2 text-white`;
  }
  if (key === "degraded" || key === "warning" || key === "expiring" || key === "restart loop" || key === "rollout aborted") {
    return `${base} bg-warning/10 text-warning`;
  }
    if (key === "open" || key === "high") {
    return `${base} bg-warning/10 text-warning`;
  }
  if (key === "acknowledged" || key === "info" || key === "running" || key === "queued" || key === "waiting") {
    return `${base} bg-action/10 text-action`;
  }
  if (key === "resolved" || key === "healthy" || key === "passing" || key === "succeeded" || key === "success" || key === "ok" || key === "connected") {
    return `${base} bg-healthy/10 text-healthy`;
  }
  if (key === "suppressed" || key === "cancelled" || key === "canceled" || key === "skipped" || key === "unknown" || key === "partial") {
    return `${base} bg-surface-low text-muted`;
  }
  if (key === "production") {
    return `${base} bg-prd text-white`;
  }
  if (key === "non-production") {
    return `${base} bg-surface-low text-ink`;
  }
  return `${base} bg-warning/10 text-warning`;
}
