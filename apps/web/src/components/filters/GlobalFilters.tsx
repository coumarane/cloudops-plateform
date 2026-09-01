import { ENVIRONMENTS, type DashboardFilters, type EnvironmentFilter, type ProviderFilter, type RegionFilter } from "@/lib/types";
import { regionsForProvider } from "@/lib/dashboard";

export function GlobalFilters({
  filters,
  onChange,
}: {
  filters: DashboardFilters;
  onChange: (filters: DashboardFilters) => void;
}) {
  const regions = regionsForProvider(filters.provider);

  return (
    <div className="flex flex-wrap items-center gap-4 border-b border-outline bg-canvas px-6 py-2 text-[11px] font-bold uppercase tracking-wide text-muted">
      <span>Global filters:</span>
      <label className="flex items-center gap-2">
        Provider:
        <select
          className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
          value={filters.provider}
          onChange={(event) => {
            const provider = event.target.value as ProviderFilter;
            const allowed = regionsForProvider(provider);
            const region =
              filters.region !== "all" && !allowed.includes(filters.region) ? "all" : filters.region;
            onChange({ ...filters, provider, region });
          }}
        >
          <option value="all">All Providers</option>
          <option value="AWS">AWS</option>
          <option value="Alibaba">Alibaba</option>
        </select>
      </label>
      <label className="flex items-center gap-2">
        Region:
        <select
          className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
          value={filters.region}
          onChange={(event) => onChange({ ...filters, region: event.target.value as RegionFilter })}
        >
          <option value="all">All Regions</option>
          {regions.map((region) => (
            <option key={region} value={region}>
              {region}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-2">
        Environment:
        <select
          className="h-6 rounded border border-outline bg-white px-2 text-[11px] font-semibold text-ink"
          value={filters.environment}
          onChange={(event) =>
            onChange({ ...filters, environment: event.target.value as EnvironmentFilter })
          }
        >
          <option value="all">All Environments</option>
          {ENVIRONMENTS.map((environment) => (
            <option key={environment} value={environment}>
              {environment}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
