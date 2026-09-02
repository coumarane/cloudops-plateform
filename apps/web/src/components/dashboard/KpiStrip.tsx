import Link from "next/link";
import type { KpiSummary } from "@/lib/types";

function Card({
  label,
  tone,
  href,
  children,
}: {
  label: string;
  tone?: "warning" | "critical";
  href?: string;
  children: React.ReactNode;
}) {
  const border =
    tone === "warning"
      ? "border-l-4 border-l-warning"
      : tone === "critical"
        ? "border-l-4 border-l-critical"
        : "";

  const body = (
    <article className={`rounded border border-outline bg-white p-3 ${border}`}>
      <p className="mb-1 truncate text-[10px] font-bold uppercase tracking-wide text-muted">{label}</p>
      {children}
    </article>
  );
  return href ? (
    <Link href={href} className="block hover:border-action">
      {body}
    </Link>
  ) : (
    body
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
  const healthy = summary.certsHealthy ?? 0;
  const expiring60 = summary.certsExpiring60d ?? 0;
  const expiring30 = summary.certsExpiring30d ?? 0;
  const expiring7 = summary.certsExpiring7d ?? 0;
  const expired = summary.certsExpired ?? 0;
  return (
    <div className="space-y-4">
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
        <Card label="Secret rotation" tone={summary.secretsOverdue > 0 ? "warning" : undefined}>
          <div className="flex items-baseline gap-1">
            <p className="text-lg font-semibold text-warning">{summary.secretsOverdue}</p>
            <span className="text-[10px] text-muted">Overdue</span>
          </div>
        </Card>
        <Card label="Failed deploys" tone={summary.failedDeploys > 0 ? "critical" : undefined}>
          <p className="text-lg font-semibold text-critical">{summary.failedDeploys}</p>
        </Card>
        <Card label="GitHub fails" tone={summary.githubFailures > 0 ? "critical" : undefined} href="/github">
          <p className="text-lg font-semibold text-critical">{summary.githubFailures}</p>
        </Card>
        <Card label="Pipeline fails" tone={summary.pipelineFailures > 0 ? "critical" : undefined} href="/pipelines">
          <p className="text-lg font-semibold text-critical">{summary.pipelineFailures}</p>
        </Card>
        <Card label="Open alerts" tone={summary.openAlerts > 0 ? "critical" : undefined}>
          <p className="text-lg font-semibold text-critical">{summary.openAlerts}</p>
        </Card>
        <Card label="Expiring certs" tone={summary.certsExpiring14d > 0 ? "warning" : undefined} href="/certificates?expires_within_days=14">
          <div className="flex items-baseline gap-1">
            <p className="text-lg font-semibold text-warning">{summary.certsExpiring14d}</p>
            <span className="text-[10px] text-muted">&lt; 14d</span>
          </div>
        </Card>
      </section>
      <section aria-label="Certificate expiry" className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Card label="Certificates healthy" href="/certificates?status=healthy">
          <p className="text-lg font-semibold text-healthy">{healthy}</p>
        </Card>
        <Card label="Expiring < 60 days" tone={expiring60 > 0 ? "warning" : undefined} href="/certificates?expires_within_days=60">
          <p className="text-lg font-semibold text-warning">{expiring60}</p>
        </Card>
        <Card label="Expiring < 30 days" tone={expiring30 > 0 ? "warning" : undefined} href="/certificates?expires_within_days=30">
          <p className="text-lg font-semibold text-warning">{expiring30}</p>
        </Card>
        <Card label="Expiring < 7 days" tone={expiring7 > 0 ? "critical" : undefined} href="/certificates?expires_within_days=7">
          <p className="text-lg font-semibold text-critical">{expiring7}</p>
        </Card>
        <Card label="Expired" tone={expired > 0 ? "critical" : undefined} href="/certificates?status=expired">
          <p className="text-lg font-semibold text-critical">{expired}</p>
        </Card>
      </section>
      <section aria-label="GitHub Workflows" className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <Card label="GitHub running" href="/github">
          <p className="text-lg font-semibold text-action">{summary.githubWorkflowsRunning ?? 0}</p>
        </Card>
        <Card label="GitHub failed" tone={(summary.githubWorkflowsFailed ?? 0) > 0 ? "critical" : undefined} href="/github">
          <p className="text-lg font-semibold text-critical">{summary.githubWorkflowsFailed ?? 0}</p>
        </Card>
        <Card label="GitHub success" href="/github">
          <p className="text-lg font-semibold text-healthy">{summary.githubWorkflowsSucceeded ?? 0}</p>
        </Card>
      </section>
      <section aria-label="Pipelines" className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Card label="Pipeline runs today" href="/pipelines">
          <p className="text-lg font-semibold text-ink">{summary.pipelineRunsToday ?? 0}</p>
        </Card>
        <Card label="Running pipelines" href="/pipelines">
          <p className="text-lg font-semibold text-action">{summary.pipelinesRunning ?? 0}</p>
        </Card>
        <Card label="Failed pipelines" tone={(summary.pipelinesFailed ?? 0) > 0 ? "critical" : undefined} href="/pipelines">
          <p className="text-lg font-semibold text-critical">{summary.pipelinesFailed ?? 0}</p>
        </Card>
        <Card label="Failed PRD pipelines" tone={(summary.pipelinesFailedPrd ?? 0) > 0 ? "critical" : undefined} href="/pipelines">
          <p className="text-lg font-semibold text-prd">{summary.pipelinesFailedPrd ?? 0}</p>
        </Card>
        <Card label="Avg deploy duration" href="/pipelines">
          <p className="text-lg font-semibold text-ink">
            {summary.pipelineAverageDurationSeconds ?? 0}
            <span className="ml-1 text-[10px] text-muted">s</span>
          </p>
        </Card>
      </section>
    </div>
  );
}
