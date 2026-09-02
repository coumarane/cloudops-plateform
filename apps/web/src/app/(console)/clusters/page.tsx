import { ClustersCatalog } from "@/components/catalog/console-pages";
import { CatalogRoute } from "../catalog-route";

export const dynamic = "force-dynamic";

export default function ClustersPage({
  searchParams,
}: {
  searchParams: Promise<{ provider?: string; region?: string; environment?: string; selected?: string }>;
}) {
  return <CatalogRoute Catalog={ClustersCatalog} label="clusters" searchParams={searchParams} />;
}
