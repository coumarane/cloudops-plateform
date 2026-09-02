import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { cellExceptionLabel, cellSeverity } from "@/lib/dashboard";
import type { CellMetrics } from "@/lib/types";

export function StatusCell({ cell, dimmed }: { cell: CellMetrics; dimmed?: boolean }) {
  const severity = cellSeverity(cell);
  const label = cellExceptionLabel(cell);

  return (
    <div className={`flex flex-col items-center gap-1 ${dimmed ? "opacity-30" : ""}`}>
      {severity === "healthy" ? (
        <CheckCircle2 className="h-4 w-4 text-healthy" aria-label="Healthy" />
      ) : null}
      {severity === "warning" ? (
        <AlertTriangle className="h-4 w-4 text-warning" aria-label={label ?? "Warning"} />
      ) : null}
      {severity === "critical" ? (
        <XCircle className="h-4 w-4 text-critical" aria-label={label ?? "Critical"} />
      ) : null}
      {label ? (
        <span
          className={
            severity === "critical"
              ? "rounded bg-critical/10 px-1 text-[9px] text-critical"
              : "rounded bg-warning/10 px-1 text-[9px] text-warning"
          }
        >
          {label}
        </span>
      ) : null}
      {cell.live ? <span className="text-[9px] font-bold uppercase tracking-wide text-action">Live</span> : null}
      {cell.readonly ? <span className="text-[9px] font-bold uppercase tracking-wide text-prd">RO</span> : null}
    </div>
  );
}
