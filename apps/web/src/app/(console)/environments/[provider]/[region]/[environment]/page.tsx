import { notFound } from "next/navigation";
import { EnvironmentDetails } from "@/components/environment/EnvironmentDetails";
import {
  environmentToSlug,
  isRegionForProvider,
  parseEnvironment,
  parseProvider,
  parseRegion,
  parseTab,
  providerToSlug,
  regionToSlug,
} from "@/lib/environment";
import { getEnvironmentRecord, listEnvironmentIdentities } from "@/lib/environment-data";

export function generateStaticParams() {
  return listEnvironmentIdentities().map((identity) => ({
    provider: providerToSlug(identity.provider),
    region: regionToSlug(identity.region),
    environment: environmentToSlug(identity.environment),
  }));
}

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
  searchParams,
}: {
  params: Promise<{ provider: string; region: string; environment: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const parsed = parseParams(await params);
  if (!parsed) {
    notFound();
  }

  const tab = parseTab((await searchParams).tab ?? null);
  const record = getEnvironmentRecord(parsed.provider, parsed.region, parsed.environment);

  return <EnvironmentDetails record={record} tab={tab} />;
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
