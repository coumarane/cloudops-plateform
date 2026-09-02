"use client";

import { useEffect, useState } from "react";

export type ResourceState<T> =
  | { status: "loading" }
  | { status: "error"; message: string; retry: () => void }
  | { status: "success"; data: T };

export function useResource<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: ReadonlyArray<unknown>,
): ResourceState<T> {
  const requestKey = JSON.stringify(deps);
  const [nonce, setNonce] = useState(0);
  const [trackedKey, setTrackedKey] = useState(requestKey);
  const [state, setState] = useState<ResourceState<T>>({ status: "loading" });

  if (trackedKey !== requestKey) {
    setTrackedKey(requestKey);
    setState({ status: "loading" });
  }

  useEffect(() => {
    const controller = new AbortController();
    loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({ status: "success", data });
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const message = error instanceof Error ? error.message : "Unable to load CloudOps data.";
        setState({
          status: "error",
          message,
          retry: () => {
            setState({ status: "loading" });
            setNonce((value) => value + 1);
          },
        });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- requestKey captures the caller-supplied dependency list
  }, [requestKey, nonce]);

  return state;
}
