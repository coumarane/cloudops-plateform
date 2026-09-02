import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { EnvBadge } from "@/components/status/EnvBadge";
import { alertHref, isPrdAlert, minutesAgo } from "@/lib/alerts";
import type { OperationalAlert } from "@/lib/types";

export function AlertsFeed({ alerts }: { alerts: OperationalAlert[] }) {
  const critical = alerts.filter((alert) => alert.severity === "critical" || isPrdAlert(alert));
  const featured = (critical.length ? critical : alerts).slice(0, 8);
  return (
    <section className="rounded border border-outline bg-white">
      <div className="flex items-center justify-between border-b border-outline bg-critical/5 p-4">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
          <AlertTriangle className="h-4 w-4 text-critical" aria-hidden />
          Critical Alerts
        </h2>
        <Link href="/alerts" className="rounded-full bg-critical px-2 py-0.5 text-[10px] font-bold text-white hover:opacity-90">
          {alerts.length} open
        </Link>
      </div>
      <div className="space-y-3 p-4">
        {featured.length === 0 ? (
          <p className="text-sm text-muted">No alerts in the current filter.</p>
        ) : (
          featured.map((alert) => (
            <article
              key={alert.id}
              className={
                alert.severity === "critical" || isPrdAlert(alert)
                  ? "rounded border border-critical/20 bg-critical/5 p-3"
                  : alert.severity === "warning"
                    ? "rounded border border-warning/20 bg-warning/5 p-3"
                    : "rounded border border-outline bg-surface-low p-3"
              }
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    {alert.severity === "critical" ? (
                      <span className="text-[10px] font-bold uppercase tracking-wide text-critical">CRITICAL</span>
                    ) : null}
                    <EnvBadge environment={alert.environment} />
                    <span className="font-mono text-[10px] text-muted">
                      {alert.provider} / {alert.region} / {alert.environment}
                    </span>
                  </div>
                  <p
                    className={
                      alert.severity === "critical"
                        ? "mb-1 text-sm font-bold text-critical"
                        : alert.severity === "warning"
                          ? "mb-1 text-sm font-bold text-warning"
                          : "mb-1 text-sm font-bold text-ink"
                    }
                  >
                    {alert.title}
                  </p>
                  <p className="font-mono text-xs text-muted">{alert.objectName}</p>
                </div>
                <span className="shrink-0 text-xs text-muted">{alert.age || minutesAgo()}</span>
              </div>
              <Link href={alert.href?.startsWith("/alerts") ? alert.href : alertHref(alert.id)} className="mt-2 inline-block text-xs font-bold text-critical hover:underline">
                Investigate →
              </Link>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
