import { Suspense } from "react";
import { PipelinesConsole } from "@/components/pipelines/PipelinesConsole";
import { parsePipelineFilters } from "@/lib/pipelines";

export const dynamic = "force-dynamic";

export default async function PipelinesPage({
  searchParams,
}: {
  searchParams: Promise<{
    provider?: string;
    region?: string;
    environment?: string;
    pipeline?: string;
    run?: string;
    tab?: string;
  }>;
}) {
  const initial = parsePipelineFilters(await searchParams);
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading pipelines…</p>}>
      <PipelinesConsole initial={initial} />
    </Suspense>
  );
}
