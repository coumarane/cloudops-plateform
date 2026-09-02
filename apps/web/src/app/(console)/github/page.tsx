import { Suspense } from "react";
import { GitHubConsole } from "@/components/github/GitHubConsole";
import { parseGithubFilters } from "@/lib/github";

export const dynamic = "force-dynamic";

export default async function GitHubPage({
  searchParams,
}: {
  searchParams: Promise<{
    provider?: string;
    region?: string;
    environment?: string;
    repo?: string;
    workflow?: string;
    run?: string;
    tab?: string;
  }>;
}) {
  const initial = parseGithubFilters(await searchParams);
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading GitHub…</p>}>
      <GitHubConsole initial={initial} />
    </Suspense>
  );
}
