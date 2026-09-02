import { environmentToSlug, providerToSlug, regionToSlug } from "@/lib/environment";
import type { Environment, Provider, Region } from "@/lib/types";
import { API_PREFIX, ApiError } from "./errors";

export type ScopeQuery = {
  provider?: Provider | "all" | null;
  region?: Region | "all" | null;
  environment?: Environment | "all" | null;
  account?: string | "all" | null;
};

export type ListResponse<T> = {
  items: T[];
  lastSynced: string;
};

export function toSearchParams(scope: ScopeQuery = {}): string {
  const params = new URLSearchParams();
  if (scope.provider && scope.provider !== "all") params.set("provider", providerToSlug(scope.provider));
  if (scope.region && scope.region !== "all") params.set("region", regionToSlug(scope.region));
  if (scope.environment && scope.environment !== "all") {
    params.set("environment", environmentToSlug(scope.environment));
  }
  if (scope.account && scope.account !== "all") params.set("account", scope.account);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function getJson<T>(path: string, scope?: ScopeQuery, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}${toSearchParams(scope)}`, {
    signal,
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(`CloudOps API request failed (${response.status})`, response.status);
  }
  return (await response.json()) as T;
}

export async function postJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    method: "POST",
    signal,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ApiError(`CloudOps API request failed (${response.status})`, response.status);
  }
  return (await response.json()) as T;
}

export async function getList<T>(path: string, scope?: ScopeQuery, signal?: AbortSignal): Promise<ListResponse<T>> {
  return getJson<ListResponse<T>>(path, scope, signal);
}
