import { ApplicationsCatalog } from "@/components/catalog/console-pages";
import { CatalogRoute } from "../catalog-route";

export const dynamic = "force-dynamic";

export default function ApplicationsPage({
  searchParams,
}: {
  searchParams: Promise<{ provider?: string; region?: string; environment?: string; selected?: string }>;
}) {
  return <CatalogRoute Catalog={ApplicationsCatalog} label="applications" searchParams={searchParams} />;
}
