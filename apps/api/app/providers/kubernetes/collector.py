from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.core.logging import get_logger
from app.providers.common.models import ClusterHealthSnapshot, DiscoveredCluster

logger = get_logger(__name__)


class KubernetesCollector(Protocol):
    def collect(
        self,
        cluster: DiscoveredCluster,
        token: str,
        ca_path: str,
        *,
        cert_path: str = "",
        key_path: str = "",
    ) -> ClusterHealthSnapshot: ...


def summarize_workload(
    *,
    node_count: int,
    ready_node_count: int,
    pod_count: int,
    unhealthy_pod_count: int,
    crashloop_backoff_count: int,
    pending_pod_count: int,
    unavailable_deployment_count: int,
    failed_job_count: int,
    stateful_set_unhealthy_count: int,
    ingress_unhealthy_count: int,
    cluster: DiscoveredCluster,
) -> ClusterHealthSnapshot:
    return ClusterHealthSnapshot(
        cluster_arn=cluster.arn,
        control_plane_status=cluster.cluster_status,
        kubernetes_api_reachable=True,
        node_count=node_count,
        ready_node_count=ready_node_count,
        pod_count=pod_count,
        unhealthy_pod_count=unhealthy_pod_count,
        crashloop_backoff_count=crashloop_backoff_count,
        pending_pod_count=pending_pod_count,
        unavailable_deployment_count=unavailable_deployment_count,
        failed_job_count=failed_job_count,
        stateful_set_unhealthy_count=stateful_set_unhealthy_count,
        ingress_unhealthy_count=ingress_unhealthy_count,
    )


class SharedKubernetesCollector:
    """Provider-neutral Kubernetes API health collector used by EKS and ACK."""

    def collect(
        self,
        cluster: DiscoveredCluster,
        token: str,
        ca_path: str,
        *,
        cert_path: str = "",
        key_path: str = "",
    ) -> ClusterHealthSnapshot:
        now = datetime.now(timezone.utc)
        if not cluster.endpoint:
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="Cluster API endpoint was not returned",
            )
        try:
            from kubernetes import client
        except ImportError:
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="Kubernetes client is not installed",
            )
        configuration = client.Configuration()
        configuration.host = cluster.endpoint
        if ca_path:
            configuration.ssl_ca_cert = ca_path
        else:
            configuration.verify_ssl = False
        if token:
            configuration.api_key = {"authorization": f"Bearer {token}"}
        if cert_path:
            configuration.cert_file = cert_path
        if key_path:
            configuration.key_file = key_path
        api_client = client.ApiClient(configuration)
        core = client.CoreV1Api(api_client)
        apps = client.AppsV1Api(api_client)
        batch = client.BatchV1Api(api_client)
        networking = client.NetworkingV1Api(api_client)
        try:
            nodes = core.list_node().items
            pods = core.list_pod_for_all_namespaces().items
            deployments = apps.list_deployment_for_all_namespaces().items
            jobs = batch.list_job_for_all_namespaces().items
            statefulsets = apps.list_stateful_set_for_all_namespaces().items
            ingresses = networking.list_ingress_for_all_namespaces().items
        except Exception as error:
            logger.warning("Kubernetes API unreachable cluster=%s error=%s", cluster.name, error)
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="Kubernetes API was not reachable",
            )
        ready_nodes = 0
        for node in nodes:
            conditions = node.status.conditions or []
            if any(condition.type == "Ready" and condition.status == "True" for condition in conditions):
                ready_nodes += 1
        crashloop = 0
        pending = 0
        unhealthy = 0
        for pod in pods:
            phase = (pod.status.phase or "").lower()
            if phase == "pending":
                pending += 1
            if phase not in {"running", "succeeded"}:
                unhealthy += 1
            for status in pod.status.container_statuses or []:
                waiting = getattr(status.state, "waiting", None)
                reason = getattr(waiting, "reason", "") if waiting else ""
                if reason == "CrashLoopBackOff":
                    crashloop += 1
        unavailable = 0
        for deployment in deployments:
            desired = deployment.spec.replicas or 0
            available = (deployment.status.available_replicas or 0) if deployment.status else 0
            if desired > available:
                unavailable += 1
        failed_jobs = 0
        for job in jobs:
            failed = (job.status.failed or 0) if job.status else 0
            if failed:
                failed_jobs += 1
        stateful_unhealthy = 0
        for item in statefulsets:
            desired = item.spec.replicas or 0
            ready = (item.status.ready_replicas or 0) if item.status else 0
            if desired > ready:
                stateful_unhealthy += 1
        ingress_unhealthy = 0
        for item in ingresses:
            ingress_status = (item.status.load_balancer.ingress if item.status and item.status.load_balancer else None) or []
            if not ingress_status:
                ingress_unhealthy += 1
        return summarize_workload(
            node_count=len(nodes),
            ready_node_count=ready_nodes,
            pod_count=len(pods),
            unhealthy_pod_count=unhealthy,
            crashloop_backoff_count=crashloop,
            pending_pod_count=pending,
            unavailable_deployment_count=unavailable,
            failed_job_count=failed_jobs,
            stateful_set_unhealthy_count=stateful_unhealthy,
            ingress_unhealthy_count=ingress_unhealthy,
            cluster=cluster,
        )


# Backwards-compatible alias used by AWS tests and collectors.
DefaultKubernetesCollector = SharedKubernetesCollector
