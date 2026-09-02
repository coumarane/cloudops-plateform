"use client";

import { useSearchParams } from "next/navigation";
import { EnvironmentIdentityHeader } from "@/components/environment/EnvironmentIdentityHeader";
import { EnvironmentTabContent } from "@/components/environment/EnvironmentTabContent";
import { EnvironmentTabs } from "@/components/environment/EnvironmentTabs";
import { PageHeader } from "@/components/layout/PageHeader";
import { parseTab } from "@/lib/environment";
import { LAST_SYNCED_LABEL } from "@/lib/mock-data";
import { environmentTitle, type EnvironmentRecord } from "@/lib/environment-data";

export function EnvironmentDetails({ record }: { record: EnvironmentRecord }) {
  const searchParams = useSearchParams();
  const tab = parseTab(searchParams.get("tab"));
  const title = environmentTitle(record.identity);

  return (
    <>
      <PageHeader title={title} subtitle="Environment details" meta={`Last synced: ${LAST_SYNCED_LABEL}`} />
      <EnvironmentIdentityHeader identity={record.identity} />
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
}

