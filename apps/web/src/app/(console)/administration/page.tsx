import { AdministrationCatalog } from "@/components/catalog/console-pages";
import { CatalogRoute } from "../catalog-route";

export const dynamic = "force-dynamic";

export default function AdministrationPage({
  searchParams,
}: {
  searchParams: Promise<{ provider?: string; region?: string; environment?: string; selected?: string }>;
}) {
  return <CatalogRoute Catalog={AdministrationCatalog} label="administration" searchParams={searchParams} />;
}
