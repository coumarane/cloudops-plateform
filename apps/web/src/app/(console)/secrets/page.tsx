import { Suspense } from "react";
import { SecretsManagement } from "@/components/secrets/SecretsManagement";
import { parseSecretsFilters } from "@/lib/secrets";

export const dynamic = "force-dynamic";

export default async function SecretsPage({
  searchParams,
}: {
  searchParams: Promise<{
    provider?: string;
    region?: string;
    account?: string;
    environment?: string;
    secret?: string;
    action?: string;
  }>;
}) {
  const initial = parseSecretsFilters(await searchParams);
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading secrets…</p>}>
      <SecretsManagement initial={initial} />
    </Suspense>
  );
}
