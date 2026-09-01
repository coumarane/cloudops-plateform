import type { KpiSummary } from "@/lib/types";

function Card({
  label,
  tone,
  children,
}: {
  label: string;
  tone?: "warning" | "critical";
  children: React.ReactNode;
}) {
  const border =
    tone === "warning"
      ? "border-l-4 border-l-warning"
      : tone === "critical"
        ? "border-l-4 border-l-critical"
        : "";

  return (
    <article className={`rounded border border-outline bg-white p-3 ${border}`}>
      <p className="mb-1 truncate text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      {children}
    </article>
  );
}

function Split({ value, suffix, tone }: { value: number; suffix: string; tone: string }) {
  return (
    <span className="flex items-baseline gap-1">
      <span className={`text-sm font-semibold ${tone}`}>{value}</span>
      <span className="text-[10px] text-muted">{suffix}</span>
    </span>
  );
}

export function KpiStrip({ summary }: { summary: KpiSummary }) {
  return (
    <section aria-label="Operational summary" className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-8">
      <Card label="Cluster health">
        <div className="flex flex-wrap gap-2">
          <Split value={summary.clustersHealthy} suffix="H" tone="text-healthy" />
          <Split value={summary.clustersDegraded} suffix="D" tone="text-warning" />
          <Split value={summary.clustersUnreachable} suffix="U" tone="text-critical" />
        </div>
      </Card>
      <Card label="App health">
        <div className="flex flex-wrap gap-2">
          <Split value={summary.appsHealthy} suffix="H" tone="text-healthy" />
          <Split value={summary.appsDegraded} suffix="D" tone="text-warning" />
        </div>
      </Card>
      <Card label="Expiring certs" tone={summary.certsExpiring14d > 0 ? "warning" : undefined}>
        <div className="flex items-baseline gap-1">
          <p className="text-lg font-semibold text-warning">{summary.certsExpiring14d}</p>
          <span className="text-[10px] text-muted">&lt; 14d</span>
        </div>
      </Card>
      <Card label="Secret rotation" tone={summary.secretsOverdue > 0 ? "warning" : undefined}>
        <div className="flex items-baseline gap-1">
          <p className="text-lg font-semibold text-warning">{summary.secretsOverdue}</p>
          <span className="text-[10px] text-muted">Overdue</span>
        </div>
      </Card>
      <Card label="Failed deploys" tone={summary.failedDeploys > 0 ? "critical" : undefined}>
        <p className="text-lg font-semibold text-critical">{summary.failedDeploys}</p>
      </Card>
      <Card label="GitHub fails" tone={summary.githubFailures > 0 ? "critical" : undefined}>
        <p className="text-lg font-semibold text-critical">{summary.githubFailures}</p>
      </Card>
      <Card label="Pipeline fails" tone={summary.pipelineFailures > 0 ? "critical" : undefined}>
        <p className="text-lg font-semibold text-critical">{summary.pipelineFailures}</p>
      </Card>
      <Card label="Open alerts" tone={summary.openAlerts > 0 ? "critical" : undefined}>
        <p className="text-lg font-semibold text-critical">{summary.openAlerts}</p>
      </Card>
    </section>
  );
}
