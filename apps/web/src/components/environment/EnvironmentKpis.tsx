import type { KpiSummary } from "@/lib/types";

function Card({
  label,
  tone,
  value,
  chip,
}: {
  label: string;
  tone?: "warning" | "critical" | "healthy";
  value: number;
  chip?: string;
}) {
  const bar =
    tone === "critical"
      ? "border-l-4 border-l-critical"
      : tone === "warning"
        ? "border-l-4 border-l-warning"
        : tone === "healthy"
          ? "border-l-4 border-l-healthy"
          : "border-l-4 border-l-outline";
  const valueClass =
    tone === "critical" ? "text-critical" : tone === "warning" ? "text-warning" : "text-ink";
  const chipClass =
    tone === "critical"
      ? "bg-critical/10 text-critical"
      : tone === "warning"
        ? "bg-warning/10 text-warning"
        : "bg-healthy/10 text-healthy";

  return (
    <article className={`relative overflow-hidden rounded border border-outline bg-white p-3 ${bar}`}>
      <p className="mb-1 truncate text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      <div className="flex items-end justify-between gap-2">
        <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
        {chip ? <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${chipClass}`}>{chip}</span> : null}
      </div>
    </article>
  );
}

export function EnvironmentKpis({ summary }: { summary: KpiSummary }) {
  const clusterTone =
    summary.clustersUnreachable > 0 ? "critical" : summary.clustersDegraded > 0 ? "warning" : "healthy";
  const clusterChip =
    summary.clustersUnreachable > 0
      ? "Unreachable"
      : summary.clustersDegraded > 0
        ? "Degraded"
        : "Healthy";
  const appTone = summary.appsDegraded > 0 ? "warning" : "healthy";
  const secretTone = summary.secretsOverdue > 0 ? "warning" : "healthy";
  const certTone = summary.certsExpiring14d > 0 ? "warning" : "healthy";

  return (
    <section aria-label="Environment summary" className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-8">
      <Card
        label="Cluster health"
        value={summary.clustersUnreachable || summary.clustersDegraded || summary.clustersHealthy}
        chip={clusterChip}
        tone={clusterTone}
      />
      <Card
        label="App health"
        value={summary.appsDegraded || summary.appsHealthy}
        chip={summary.appsDegraded > 0 ? "Degraded" : "Healthy"}
        tone={appTone}
      />
      <Card
        label="Cert expiration"
        value={summary.certsExpiring14d}
        chip="Expiring"
        tone={certTone}
      />
      <Card
        label="Secret rotation"
        value={summary.secretsOverdue}
        chip={summary.secretsOverdue > 0 ? "Overdue" : "Current"}
        tone={secretTone}
      />
      <Card
        label="Failed deploys"
        value={summary.failedDeploys}
        tone={summary.failedDeploys > 0 ? "critical" : "healthy"}
      />
      <Card
        label="GitHub failures"
        value={summary.githubFailures}
        tone={summary.githubFailures > 0 ? "critical" : "healthy"}
      />
      <Card
        label="Pipeline fails"
        value={summary.pipelineFailures}
        tone={summary.pipelineFailures > 0 ? "critical" : "healthy"}
      />
      <Card
        label="Op alerts"
        value={summary.openAlerts}
        chip={summary.openAlerts > 0 ? "Critical" : undefined}
        tone={summary.openAlerts > 0 ? "critical" : "healthy"}
      />
    </section>
  );
}
