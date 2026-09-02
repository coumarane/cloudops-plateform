"use client";

import { useMemo, useState } from "react";
import { AlertsFeed } from "@/components/dashboard/AlertsFeed";
import { FailuresList } from "@/components/dashboard/FailuresList";
import { HealthMatrix } from "@/components/dashboard/HealthMatrix";
import { KpiStrip } from "@/components/dashboard/KpiStrip";
import { GlobalFilters } from "@/components/filters/GlobalFilters";
import { PageHeader } from "@/components/layout/PageHeader";
import { filterAlerts, filterFailures, filterRows, summarizeKpis } from "@/lib/dashboard";
import { LAST_SYNCED_LABEL, MATRIX_ROWS, OPERATIONAL_ALERTS, RECENT_FAILURES } from "@/lib/mock-data";
import type { DashboardFilters } from "@/lib/types";

const INITIAL_FILTERS: DashboardFilters = {
  provider: "all",
  region: "all",
  environment: "all",
};

export function OperationsDashboard() {
  const [filters, setFilters] = useState<DashboardFilters>(INITIAL_FILTERS);

  const rows = useMemo(() => filterRows(MATRIX_ROWS, filters), [filters]);
  const alerts = useMemo(() => filterAlerts(OPERATIONAL_ALERTS, filters), [filters]);
  const failures = useMemo(() => filterFailures(RECENT_FAILURES, filters), [filters]);
  const summary = useMemo(() => summarizeKpis(MATRIX_ROWS, filters), [filters]);

  return (
    <>
      <PageHeader
        title="Global Operations Dashboard"
        subtitle="Multi-cloud EKS and ACK health across AWS AMER, EMEA, APAC and Alibaba China"
        meta={`Last synced: ${LAST_SYNCED_LABEL}`}
      />
      <GlobalFilters filters={filters} onChange={setFilters} />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-[1600px] space-y-6">
          <KpiStrip summary={summary} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <HealthMatrix rows={rows} filters={filters} />
            </div>
            <div className="space-y-6">
              <AlertsFeed alerts={alerts} />
              <FailuresList failures={failures} />
            </div>
          </div>
          <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
            Secret values are never displayed in this console.
          </p>
        </div>
      </main>
    </>
  );
}
