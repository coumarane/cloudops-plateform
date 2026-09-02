import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { EnvBadge } from "@/components/status/EnvBadge";
import type { OperationalAlert } from "@/lib/types";

export function AlertsFeed({ alerts }: { alerts: OperationalAlert[] }) {
  return (
    <section className="rounded border border-outline bg-white">
      <div className="flex items-center justify-between border-b border-outline bg-critical/5 p-4">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
          <AlertTriangle className="h-4 w-4 text-critical" aria-hidden />
          Operational Alerts
        </h2>
        <span className="rounded-full bg-critical px-2 py-0.5 text-[10px] font-bold text-white">
          {alerts.length} open
        </span>
      </div>
      <div className="space-y-3 p-4">
        {alerts.length === 0 ? (
          <p className="text-sm text-muted">No alerts in the current filter.</p>
        ) : (
          alerts.map((alert) => (
            <article
              key={alert.id}
              className={
                alert.severity === "critical"
                  ? "rounded border border-critical/20 bg-critical/5 p-3"
                  : alert.severity === "warning"
                    ? "rounded border border-warning/20 bg-warning/5 p-3"
                    : "rounded border border-outline bg-surface-low p-3"
              }
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    <EnvBadge environment={alert.environment} />
                    <span className="font-mono text-[10px] text-muted">{alert.region}</span>
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
                <span className="shrink-0 text-xs text-muted">{alert.age}</span>
              </div>
              <Link
                href={alert.href}
                className={
                  alert.severity === "critical"
                    ? "mt-2 inline-block text-xs font-bold text-critical hover:underline"
                    : "mt-2 inline-block text-xs font-bold text-action hover:underline"
                }
              >
                Investigate →
              </Link>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
