import { environmentToSlug, providerToSlug, regionToSlug } from "@/lib/environment";
import type { Environment, Provider, Region } from "@/lib/types";
import { API_PREFIX, ApiError } from "./errors";

export type ScopeQuery = {
  provider?: Provider | "all" | null;
  region?: Region | "all" | null;
  environment?: Environment | "all" | null;
  account?: string | "all" | null;
  status?: string | null;
  expiresWithinDays?: number | string | null;
  sort?: string | null;
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
  if (scope.status) params.set("status", scope.status);
  if (scope.expiresWithinDays) params.set("expires_within_days", String(scope.expiresWithinDays));
  if (scope.sort) params.set("sort", scope.sort);
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
    throw await toApiError(response);
  }
  return (await response.json()) as T;
}

export async function postJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  return postJsonBody<T>(path, undefined, signal);
}

export async function postJsonBody<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return sendJson<T>("POST", path, body, signal);
}

export async function putJsonBody<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return sendJson<T>("PUT", path, body, signal);
}

export async function deleteJson<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return sendJson<T>("DELETE", path, body, signal);
}

async function sendJson<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    method,
    signal,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail = `CloudOps API request failed (${response.status})`;
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail) {
      detail = payload.detail;
    }
  } catch {
    // Response body is not JSON; keep the status message.
  }
  return new ApiError(detail, response.status);
}

export async function getList<T>(path: string, scope?: ScopeQuery, signal?: AbortSignal): Promise<ListResponse<T>> {
  return getJson<ListResponse<T>>(path, scope, signal);
}
