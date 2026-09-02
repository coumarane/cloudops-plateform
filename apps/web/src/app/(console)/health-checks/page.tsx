import { HealthChecksCatalog } from "@/components/catalog/console-pages";
import { CatalogRoute } from "../catalog-route";

export const dynamic = "force-dynamic";

export default function HealthChecksPage({
  searchParams,
}: {
  searchParams: Promise<{ provider?: string; region?: string; environment?: string; selected?: string }>;
}) {
  return <CatalogRoute Catalog={HealthChecksCatalog} label="health checks" searchParams={searchParams} />;
}
