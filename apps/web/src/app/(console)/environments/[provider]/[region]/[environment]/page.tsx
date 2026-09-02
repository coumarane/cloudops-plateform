import { notFound } from "next/navigation";
import { Suspense } from "react";
import { EnvironmentDetails } from "@/components/environment/EnvironmentDetails";
import {
  environmentToSlug,
  isRegionForProvider,
  parseEnvironment,
  parseProvider,
  parseRegion,
  providerToSlug,
  regionToSlug,
} from "@/lib/environment";
import { listEnvironmentIdentities } from "@/lib/environment-data";

export function generateStaticParams() {
  return listEnvironmentIdentities().map((identity) => ({
    provider: providerToSlug(identity.provider),
    region: regionToSlug(identity.region),
    environment: environmentToSlug(identity.environment),
  }));
}

export const dynamicParams = false;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ provider: string; region: string; environment: string }>;
}) {
  const parsed = parseParams(await params);
  if (!parsed) {
    return { title: "Environment | CloudOps Platform" };
  }
  return {
    title: `${parsed.provider} ${parsed.region} ${parsed.environment} | CloudOps Platform`,
  };
}

export default async function EnvironmentDetailsPage({
  params,
}: {
  params: Promise<{ provider: string; region: string; environment: string }>;
}) {
  const parsed = parseParams(await params);
  if (!parsed) {
    notFound();
  }

  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading environment…</p>}>
      <EnvironmentDetails
        provider={parsed.provider}
        region={parsed.region}
        environment={parsed.environment}
      />
    </Suspense>
  );
}

function parseParams(params: { provider: string; region: string; environment: string }) {
  const provider = parseProvider(params.provider);
  const region = parseRegion(params.region);
  const environment = parseEnvironment(params.environment);
  if (!provider || !region || !environment || !isRegionForProvider(provider, region)) {
    return null;
  }
  return { provider, region, environment };
}
