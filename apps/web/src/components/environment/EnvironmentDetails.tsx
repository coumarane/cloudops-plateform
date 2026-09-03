"use client";

import { useSearchParams } from "next/navigation";
import { EnvironmentActions } from "@/components/environment/EnvironmentActions";
import { EnvironmentIdentityHeader } from "@/components/environment/EnvironmentIdentityHeader";
import { EnvironmentTabContent } from "@/components/environment/EnvironmentTabContent";
import { EnvironmentTabs } from "@/components/environment/EnvironmentTabs";
import { PageHeader } from "@/components/layout/PageHeader";
import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import { environmentToSlug, parseTab, providerToSlug, regionToSlug } from "@/lib/environment";
import { environmentTitle } from "@/lib/environment-data";
import type { Environment, Provider, Region } from "@/lib/types";

export function EnvironmentDetails({
  provider,
  region,
  environment,
}: {
  provider: Provider;
  region: Region;
  environment: Environment;
}) {
  const searchParams = useSearchParams();
  const tab = parseTab(searchParams.get("tab"));
  const state = useResource(
    (signal) =>
      cloudOpsApi.environment(providerToSlug(provider), regionToSlug(region), environmentToSlug(environment), signal),
    [provider, region, environment],
  );

  return (
    <QueryState state={state} loadingLabel="Loading environment…">
      {(record) => {
        const title = environmentTitle(record.identity);
        return (
          <>
            <PageHeader
              title={title}
              subtitle="Environment details"
              meta={`Last synced: ${record.lastSynced ?? "—"}`}
            />
            <EnvironmentIdentityHeader identity={record.identity} />
            <div className="border-b border-outline bg-white px-6 py-4">
              <EnvironmentActions identity={record.identity} />
            </div>
            <EnvironmentTabs identity={record.identity} current={tab} />
            <main className="flex-1 overflow-y-auto p-6 pb-16">
              <div className="mx-auto max-w-[1600px] space-y-6">
                <EnvironmentTabContent record={record} tab={tab} />
                <p className="border-t border-outline pt-4 text-center font-mono text-xs text-muted">
                  Secret values are never displayed in this console.
                </p>
              </div>
            </main>
          </>
        );
      }}
    </QueryState>
  );
}
