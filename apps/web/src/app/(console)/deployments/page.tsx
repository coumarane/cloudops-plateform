import { DeploymentsCatalog } from "@/components/catalog/console-pages";
import { CatalogRoute } from "../catalog-route";

export const dynamic = "force-dynamic";

export default function DeploymentsPage({
  searchParams,
}: {
  searchParams: Promise<{ provider?: string; region?: string; environment?: string; selected?: string }>;
}) {
  return <CatalogRoute Catalog={DeploymentsCatalog} label="deployments" searchParams={searchParams} />;
}
