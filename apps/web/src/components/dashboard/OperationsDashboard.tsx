"use client";

import Link from "next/link";
import { AlertsFeed } from "@/components/dashboard/AlertsFeed";
import { FailuresList } from "@/components/dashboard/FailuresList";
import { HealthMatrix } from "@/components/dashboard/HealthMatrix";
import { KpiStrip } from "@/components/dashboard/KpiStrip";
import { GlobalFilters } from "@/components/filters/GlobalFilters";
import { PageHeader } from "@/components/layout/PageHeader";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import type { DashboardSnapshot } from "@/lib/domain";
import type { DashboardFilters } from "@/lib/types";
import { useState } from "react";

const INITIAL_FILTERS: DashboardFilters = {
  provider: "all",
  region: "all",
  environment: "all",
};

export function OperationsDashboard() {
  const [filters, setFilters] = useState<DashboardFilters>(INITIAL_FILTERS);
  const state = useResource(
    (signal) => cloudOpsApi.dashboard(filters, signal),
    [filters.provider, filters.region, filters.environment],
  );

  return (
    <>
      <PageHeader
        title="Global Operations Dashboard"
        subtitle="Multi-cloud EKS and ACK health across AWS AMER, EMEA, APAC and Alibaba China"
        meta={state.status === "success" ? `Last synced: ${state.data.lastSynced}` : "Last synced: —"}
      />
      <GlobalFilters filters={filters} onChange={setFilters} />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <QueryState state={state} loadingLabel="Loading operations dashboard…">
            {(data: DashboardSnapshot) =>
              data.onboarding ? (
                <OnboardingPanel />
              ) : data.matrix.length === 0 ? (
                <div className="rounded border border-outline bg-white p-6">
                  <p className="text-sm text-muted">No inventory in the current filter.</p>
                  <Link href="/administration?section=providers" className="mt-3 inline-block rounded bg-action px-3 py-1.5 text-xs font-semibold text-white">
                    Add Provider
                  </Link>
                </div>
              ) : (
                <>
                  <KpiStrip summary={data.kpis} />
                  <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                    <div className="lg:col-span-2">
                      <HealthMatrix rows={data.matrix} filters={filters} />
                    </div>
                    <div className="space-y-6">
                      <AlertsFeed alerts={data.alerts} />
                      <FailuresList failures={data.failures} />
                    </div>
                  </div>
                </>
              )
            }
          </QueryState>
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Secret values are never displayed in this console.
          </p>
        </div>
      </main>
    </>
  );
}

function OnboardingPanel() {
  return (
    <section className="rounded border border-outline bg-white p-6">
      <h2 className="text-lg font-semibold text-ink">Welcome to CloudOps Platform</h2>
      <p className="mt-2 text-sm text-muted">No cloud providers configured. Mock infrastructure is disabled until you complete setup.</p>
      <ol className="mt-4 list-decimal space-y-1 pl-5 text-sm text-ink">
        <li>Configure Cloud Provider</li>
        <li>Configure Cloud Account</li>
        <li>Create Environment</li>
        <li>Configure Authentication</li>
        <li>Validate Connection</li>
        <li>Discover Resources</li>
      </ol>
      <Link href="/administration?section=providers" className="mt-4 inline-block rounded bg-action px-4 py-2 text-sm font-semibold text-white">
        Start Setup
      </Link>
    </section>
  );
}
