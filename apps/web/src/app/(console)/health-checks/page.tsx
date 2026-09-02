import { Suspense } from "react";
import { HealthConsole } from "@/components/health/HealthConsole";
import { parseHealthFilters } from "@/lib/health";

export const dynamic = "force-dynamic";

export default async function HealthChecksPage({
  searchParams,
}: {
  searchParams: Promise<{
    provider?: string;
    region?: string;
    environment?: string;
    app?: string;
    incident?: string;
    tab?: string;
    cluster?: string;
  }>;
}) {
  const initial = parseHealthFilters(await searchParams);
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading health…</p>}>
      <HealthConsole initial={initial} />
    </Suspense>
  );
}
