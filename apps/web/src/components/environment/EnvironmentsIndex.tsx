"use client";

import Link from "next/link";
import { PageHeader } from "@/components/layout/PageHeader";
import { QueryState } from "@/components/status/QueryState";
import { StatusCell } from "@/components/status/StatusCell";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import { environmentHref } from "@/lib/environment";
import {
  ENVIRONMENTS,
  NON_PRODUCTION_ENVIRONMENTS,
  PRODUCTION_ENVIRONMENTS,
  type Environment,
  type MatrixRow,
  type Provider,
} from "@/lib/types";

const PROVIDER_GROUPS: { provider: Provider; label: string }[] = [
  { provider: "AWS", label: "AWS | EKS | AMER · EMEA · APAC" },
  { provider: "Alibaba", label: "Alibaba | ACK | China" },
];

export function EnvironmentsIndex() {
  const state = useResource((signal) => cloudOpsApi.dashboard({}, signal), []);

  return (
    <>
      <PageHeader
        title="Environments"
        subtitle="Select a provider, region, and environment to open operational details"
        meta={state.status === "success" ? `Last synced: ${state.data.lastSynced}` : "Last synced: —"}
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState
            state={state}
            loadingLabel="Loading environment catalog…"
            emptyLabel="No environments configured."
            isEmpty={(data) => data.matrix.length === 0}
            emptyAction={
              <a href="/administration?section=environments" className="rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
                Add Environment
              </a>
            }
          >
            {(data) => (
              <section className="rounded border border-outline bg-white">
                <div className="border-b border-outline p-4">
                  <h2 className="text-lg font-semibold text-ink">Environment catalog</h2>
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
                      {PROVIDER_GROUPS.map((group) => (
                        <ProviderGroup
                          key={group.provider}
                          label={group.label}
                          rows={data.matrix.filter((row) => row.provider === group.provider)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </QueryState>
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Secret values are never displayed in this console.
          </p>
        </div>
      </main>
    </>
  );
}

function ProviderGroup({ label, rows }: { label: string; rows: MatrixRow[] }) {
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
          {ENVIRONMENTS.map((environment: Environment) => (
            <td
              key={environment}
              className={environment === "NPD" ? "border-l border-outline p-2 text-center" : "p-2 text-center"}
            >
              <Link
                href={environmentHref(row.provider, row.region, environment)}
                className="inline-flex flex-col items-center gap-1 hover:underline"
                aria-label={`${row.provider} ${row.region} ${environment} details`}
              >
                <StatusCell cell={row.cells[environment]} />
              </Link>
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
