"use client";

import { QueryState } from "@/components/status/QueryState";
import { cloudOpsApi } from "@/lib/api/client";
import { useResource } from "@/lib/api/use-resource";
import type { ClusterHealthRecord } from "@/lib/domain";

export function ClusterHealthPanel({ clusterId }: { clusterId: string }) {
  const state = useResource((signal) => cloudOpsApi.clusterHealth(clusterId, signal), [clusterId]);
  const resourcesState = useResource(
    (signal) => cloudOpsApi.healthResources({ cluster: clusterId }, signal),
    [clusterId],
  );

  return (
    <section className="rounded border border-outline bg-white">
      <div className="border-b border-outline bg-surface-low px-4 py-3">
        <h2 className="text-[15px] font-semibold text-ink">Live cluster health</h2>
        <p className="mt-1 text-xs text-muted">Control-plane and Kubernetes API metadata from the shared collector. AWS EKS and Alibaba ACK use the same health model. Kubeconfig is never displayed.</p>
      </div>
      <div className="space-y-4 p-4">
        <QueryState state={state} loadingLabel="Loading cluster health…" emptyLabel="Health has not been collected yet.">
          {(data: ClusterHealthRecord) => (
            <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              <Metric label="API" value={data.kubernetesApiReachable ? "Reachable" : "Unreachable"} />
              <Metric label="Control plane" value={data.controlPlaneStatus} />
              <Metric label="Nodes" value={`${data.readyNodeCount}/${data.nodeCount}`} />
              <Metric label="Pods" value={`${data.podCount}`} />
              <Metric label="Unhealthy pods" value={`${data.unhealthyPodCount}`} />
              <Metric label="CrashLoopBackOff" value={`${data.crashLoopBackOffCount}`} />
              <Metric label="Deployments unavailable" value={`${data.unavailableDeploymentCount}`} />
              <Metric label="StatefulSets" value={`${data.statefulSetUnhealthyCount ?? 0}`} />
              <Metric label="Jobs failed" value={`${data.failedJobCount}`} />
              <Metric label="Ingress" value={`${data.ingressUnhealthyCount ?? 0} unhealthy`} />
              <Metric label="Last checked" value={data.lastChecked} />
            </dl>
          )}
        </QueryState>
        <QueryState state={resourcesState} loadingLabel="Loading namespace resources…" emptyLabel="No normalized resources for this cluster." isEmpty={(data) => data.items.length === 0}>
          {(data) => {
            const namespaces = [...new Set(data.items.map((item) => item.namespace || "(cluster)"))];
            return (
              <div className="space-y-3">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted">Cluster → Namespace → Resource</p>
                {namespaces.map((namespace) => (
                  <details key={namespace} className="rounded border border-outline">
                    <summary className="cursor-pointer bg-surface-low px-3 py-2 font-mono text-xs">{namespace}</summary>
                    <ul className="divide-y divide-outline">
                      {data.items
                        .filter((item) => (item.namespace || "(cluster)") === namespace)
                        .map((item) => (
                          <li key={item.id} className="flex items-center justify-between px-3 py-2 font-mono text-xs">
                            <span>
                              {item.resourceType}/{item.name}
                            </span>
                            <span className="text-muted">{item.status}</span>
                          </li>
                        ))}
                    </ul>
                  </details>
                ))}
              </div>
            );
          }}
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
