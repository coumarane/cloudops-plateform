"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { regionsForProvider } from "@/lib/dashboard";
import type { CatalogFilters } from "@/lib/catalog";
import {
  environmentToSlug,
  parseEnvironment,
  parseProvider,
  parseRegion,
  providerToSlug,
  regionToSlug,
} from "@/lib/environment";
import { ENVIRONMENTS, type Environment, type Provider, type Region } from "@/lib/types";

export function useCatalogFilters(initial: CatalogFilters) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const provider = parseProvider(searchParams.get("provider") ?? "") ?? initial.provider ?? "all";
  const region = parseRegion(searchParams.get("region") ?? "") ?? initial.region ?? "all";
  const environment =
    parseEnvironment(searchParams.get("environment") ?? "") ?? initial.environment ?? "all";
  const selected = searchParams.get("selected") || initial.selected;
  const regions = regionsForProvider(provider === "all" ? "all" : provider);
  const scopedRegion = region !== "all" && !regions.includes(region) ? "all" : region;

  function setFilter(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(next)) {
      if (!value || value === "all") params.delete(key);
      else params.set(key, value);
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  return {
    provider: provider as Provider | "all",
    region: scopedRegion as Region | "all",
    environment: environment as Environment | "all",
    selected,
    regions,
    setFilter,
  };
}

export function HierarchyFilters({
  provider,
  region,
  environment,
  regions,
  setFilter,
}: {
  provider: Provider | "all";
  region: Region | "all";
  environment: Environment | "all";
  regions: Region[];
  setFilter: (next: Record<string, string | null>) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4 border-b border-outline bg-canvas px-6 py-2 text-[11px] font-bold uppercase tracking-wide text-muted">
      <span>Hierarchy:</span>
      <label className="flex items-center gap-2">
        Provider:
        <select
          className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
          value={provider === "all" ? "all" : providerToSlug(provider)}
          onChange={(event) => setFilter({ provider: event.target.value, region: null })}
        >
          <option value="all">All providers</option>
          <option value="aws">AWS</option>
          <option value="alibaba">Alibaba</option>
        </select>
      </label>
      <label className="flex items-center gap-2">
        Region:
        <select
          className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
          value={region === "all" ? "all" : regionToSlug(region)}
          onChange={(event) => setFilter({ region: event.target.value })}
        >
          <option value="all">All regions</option>
          {regions.map((item) => (
            <option key={item} value={regionToSlug(item)}>
              {item}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2">
        Environment:
        <select
          className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
          value={environment === "all" ? "all" : environmentToSlug(environment)}
          onChange={(event) => setFilter({ environment: event.target.value })}
        >
          <option value="all">All environments</option>
          {ENVIRONMENTS.map((item) => (
            <option key={item} value={environmentToSlug(item)}>
              {item}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
