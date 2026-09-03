"use client";

import type { ReactNode } from "react";
import type { ResourceState } from "@/lib/api/use-resource";

export function QueryState<T>({
  state,
  loadingLabel,
  emptyLabel,
  isEmpty,
  emptyAction,
  children,
}: {
  state: ResourceState<T>;
  loadingLabel: string;
  emptyLabel?: string;
  isEmpty?: (data: T) => boolean;
  emptyAction?: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (state.status === "loading") {
    return (
      <div className="rounded border border-outline bg-white p-6" role="status">
        <p className="text-sm text-muted">{loadingLabel}</p>
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="rounded border border-critical/40 bg-critical/5 p-6" role="alert">
        <p className="text-sm font-semibold text-critical">Unable to load data from the CloudOps API.</p>
        <p className="mt-1 text-sm text-muted">{state.message}</p>
        <button
          type="button"
          className="mt-3 rounded border border-critical px-3 py-1 text-xs font-bold uppercase tracking-wide text-critical"
          onClick={state.retry}
        >
          Retry
        </button>
      </div>
    );
  }
  if (isEmpty?.(state.data)) {
    return (
      <div className="rounded border border-outline bg-white p-6">
        <p className="text-sm text-muted">{emptyLabel ?? "No records in the current filter."}</p>
        {emptyAction ? <div className="mt-3">{emptyAction}</div> : null}
      </div>
    );
  }
  return <>{children(state.data)}</>;
}
