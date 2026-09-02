import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { StatusCell } from "@/components/status/StatusCell";
import { environmentHref } from "@/lib/environment";
import {
  ENVIRONMENTS,
  NON_PRODUCTION_ENVIRONMENTS,
  PRODUCTION_ENVIRONMENTS,
  type DashboardFilters,
  type MatrixRow,
  type Provider,
} from "@/lib/types";

const PROVIDER_GROUPS: { provider: Provider; label: string }[] = [
  { provider: "AWS", label: "AWS | EKS | AMER · EMEA · APAC" },
  { provider: "Alibaba", label: "Alibaba | ACK | China" },
];

export function HealthMatrix({
  rows,
  filters,
}: {
  rows: MatrixRow[];
  filters: DashboardFilters;
}) {
  return (
    <section className="rounded border border-outline bg-white">
      <div className="flex items-center justify-between border-b border-outline p-4">
        <h2 className="text-lg font-semibold text-ink">Infrastructure Health Matrix</h2>
        <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-action">
          <RefreshCw className="h-3.5 w-3.5" aria-hidden />
          Live
        </span>
      </div>
      <div className="overflow-x-auto p-4">
        <table className="w-full border-collapse text-left text-[13px]">
          <thead>
            <tr>
              <th className="p-2" />
              <th
                className="p-2 text-center text-[11px] font-bold uppercase tracking-wide text-muted"
                colSpan={NON_PRODUCTION_ENVIRONMENTS.length}
              >
                Non-production
              </th>
              <th
                className="p-2 text-center text-[11px] font-bold uppercase tracking-wide text-prd"
                colSpan={PRODUCTION_ENVIRONMENTS.length}
              >
                <div className="border-t-4 border-prd pt-1">Production</div>
              </th>
            </tr>
            <tr className="border-b border-outline">
              <th className="p-2 text-[11px] font-bold uppercase tracking-wide text-muted">Region</th>
              {ENVIRONMENTS.map((environment) => (
                <th
                  key={environment}
                  className={
                    environment === "PRD"
                      ? "p-2 text-center text-[11px] font-bold uppercase tracking-wide text-prd"
                      : "p-2 text-center text-[11px] font-bold uppercase tracking-wide text-muted"
                  }
                >
                  {environment}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PROVIDER_GROUPS.map((group) => {
              const groupRows = rows.filter((row) => row.provider === group.provider);
              if (groupRows.length === 0) {
                return null;
              }
              return (
                <ProviderGroup
                  key={group.provider}
                  label={group.label}
                  rows={groupRows}
                  environmentFilter={filters.environment}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProviderGroup({
  label,
  rows,
  environmentFilter,
}: {
  label: string;
  rows: MatrixRow[];
  environmentFilter: DashboardFilters["environment"];
}) {
  return (
    <>
      <tr>
        <td className="bg-surface-low p-2 text-xs font-bold uppercase tracking-wide text-ink" colSpan={6}>
          {label}
        </td>
      </tr>
      {rows.map((row, index) => (
        <tr
          key={`${row.provider}-${row.region}`}
          className={index === rows.length - 1 ? "" : "border-b border-outline"}
        >
          <td className="p-2 font-mono text-xs text-ink">{row.region}</td>
          {ENVIRONMENTS.map((environment) => (
            <td
              key={environment}
              className={environment === "NPD" ? "border-l border-outline p-2 text-center" : "p-2 text-center"}
            >
              <Link
                href={environmentHref(row.provider, row.region, environment)}
                className="inline-flex"
                aria-label={`${row.provider} ${row.region} ${environment} environment details`}
              >
                <StatusCell
                  cell={row.cells[environment]}
                  dimmed={environmentFilter !== "all" && environmentFilter !== environment}
                />
              </Link>
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
