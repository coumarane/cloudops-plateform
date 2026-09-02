"use client";

import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import type { ClusterHealthRecord } from "@/lib/domain";

export function ClusterHealthPanel({ clusterId }: { clusterId: string }) {
  const state = useResource((signal) => cloudOpsApi.clusterHealth(clusterId, signal), [clusterId]);

  return (
    <section className="rounded border border-outline bg-white">
      <div className="border-b border-outline bg-surface-low px-4 py-3">
        <h2 className="text-[15px] font-semibold text-ink">Live cluster health</h2>
        <p className="mt-1 text-xs text-muted">AWS EMEA DEV control-plane and Kubernetes API metadata. Kubeconfig is never displayed.</p>
      </div>
      <div className="p-4">
        <QueryState state={state} loadingLabel="Loading cluster health…" emptyLabel="Health has not been collected yet.">
          {(data: ClusterHealthRecord) => (
            <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              <Metric label="Control plane" value={data.controlPlaneStatus} />
              <Metric label="API reachable" value={data.kubernetesApiReachable ? "Yes" : "No"} />
              <Metric label="Ready nodes" value={`${data.readyNodeCount}/${data.nodeCount}`} />
              <Metric label="Pods" value={`${data.podCount}`} />
              <Metric label="Unhealthy pods" value={`${data.unhealthyPodCount}`} />
              <Metric label="CrashLoopBackOff" value={`${data.crashLoopBackOffCount}`} />
              <Metric label="Pending pods" value={`${data.pendingPodCount}`} />
              <Metric label="Unavailable deployments" value={`${data.unavailableDeploymentCount}`} />
              <Metric label="Failed jobs" value={`${data.failedJobCount}`} />
              <Metric label="Last checked" value={data.lastChecked} />
            </dl>
          )}
        </QueryState>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] font-bold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="font-mono text-xs text-ink">{value}</dd>
    </div>
  );
}
