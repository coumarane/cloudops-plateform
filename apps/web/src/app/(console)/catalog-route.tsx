import { Suspense, type ComponentType } from "react";
import { parseCatalogFilters, type CatalogFilters } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export function CatalogRoute({
  Catalog,
  label,
  searchParams,
}: {
  Catalog: ComponentType<{ initial: CatalogFilters }>;
  label: string;
  searchParams: Promise<{
    provider?: string;
    region?: string;
    environment?: string;
    selected?: string;
  }>;
}) {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-muted">Loading {label}…</p>}>
      <CatalogLoader Catalog={Catalog} searchParams={searchParams} />
    </Suspense>
  );
}

async function CatalogLoader({
  Catalog,
  searchParams,
}: {
  Catalog: ComponentType<{ initial: CatalogFilters }>;
  searchParams: Promise<{
    provider?: string;
    region?: string;
    environment?: string;
    selected?: string;
  }>;
}) {
  const initial = parseCatalogFilters(await searchParams);
  return <Catalog initial={initial} />;
}
