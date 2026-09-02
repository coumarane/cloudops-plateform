from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from app.core.logging import get_logger
from app.providers.common.models import ClusterHealthSnapshot, DiscoveredCluster

logger = get_logger(__name__)


def inventory_payload(collector, cluster, *args, **kwargs):
    """Call collect_inventory when available; otherwise fall back to collect().

    MagicMock collectors used in AWS/Alibaba tests only stub collect(). Those
    mocks are callable but do not return a real (snapshot, resources) tuple, so
    this helper must not unpack them as inventory.
    """
    method = getattr(collector, "collect_inventory", None)
    if callable(method):
        payload = method(cluster, *args, **kwargs)
        if (
            isinstance(payload, tuple)
            and len(payload) == 2
            and hasattr(payload[0], "kubernetes_api_reachable")
            and isinstance(payload[1], list)
        ):
            snapshot, resources = payload
            return snapshot, list(resources)
    return collector.collect(cluster, *args, **kwargs), []


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


def _unreachable_snapshot(cluster: DiscoveredCluster, detail: str) -> ClusterHealthSnapshot:
    return ClusterHealthSnapshot(
        cluster_arn=cluster.arn,
        control_plane_status=cluster.cluster_status,
        kubernetes_api_reachable=False,
        last_checked=datetime.now(timezone.utc),
        detail=detail,
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
        snapshot, _resources = self.collect_inventory(
            cluster, token, ca_path, cert_path=cert_path, key_path=key_path
        )
        return snapshot

    def collect_inventory(
        self,
        cluster: DiscoveredCluster,
        token: str,
        ca_path: str,
        *,
        cert_path: str = "",
        key_path: str = "",
    ):
        from app.integrations.health.normalize import (
            NormalizedResource,
            normalize_cluster,
            normalize_daemonset,
            normalize_deployment,
            normalize_ingress,
            normalize_job,
            normalize_node,
            normalize_pod,
            normalize_service,
            normalize_statefulset,
            snapshot_from_resources,
        )
        from app.integrations.health.status import worst

        def _fail(detail: str):
            snapshot = _unreachable_snapshot(cluster, detail)
            return snapshot, [
                normalize_cluster(
                    reachable=False,
                    cluster_status=cluster.cluster_status,
                    detail=detail,
                )
            ]

        if not cluster.endpoint:
            return _fail("Cluster API endpoint was not returned")
        try:
            from kubernetes import client
        except ImportError:
            return _fail("Kubernetes client is not installed")
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
        git_version = getattr(cluster, "kubernetes_version", "") or ""
        try:
            info = client.VersionApi(api_client).get_code()
            raw = getattr(info, "git_version", "") if info is not None else ""
            if isinstance(raw, str) and raw:
                git_version = raw
        except Exception:
            pass
        try:
            nodes = core.list_node().items or []
            pods = core.list_pod_for_all_namespaces().items or []
            deployments = apps.list_deployment_for_all_namespaces().items or []
            statefulsets = apps.list_stateful_set_for_all_namespaces().items or []
            daemonsets = apps.list_daemon_set_for_all_namespaces().items or []
            jobs = batch.list_job_for_all_namespaces().items or []
            services = core.list_service_for_all_namespaces().items or []
            ingresses = networking.list_ingress_for_all_namespaces().items or []
        except Exception as error:
            logger.warning("Kubernetes API unreachable cluster=%s error=%s", cluster.name, error)
            return _fail("Kubernetes API was not reachable")
        resources = [
            normalize_cluster(
                reachable=True,
                version=git_version,
                cluster_status=cluster.cluster_status,
            )
        ]
        resources.extend(normalize_node(item) for item in nodes)
        resources.extend(normalize_pod(item) for item in pods)
        resources.extend(normalize_deployment(item) for item in deployments)
        resources.extend(normalize_statefulset(item) for item in statefulsets)
        resources.extend(normalize_daemonset(item) for item in daemonsets)
        resources.extend(normalize_job(item) for item in jobs)
        for service in services:
            ready = 0
            try:
                endpoints = core.read_namespaced_endpoints(service.metadata.name, service.metadata.namespace)
                subsets = endpoints.subsets or []
                ready = sum(len(subset.addresses or []) for subset in subsets)
            except Exception:
                ready = 0
            resources.append(normalize_service(service, endpoint_ready=ready, endpoint_expected=1))
        resources.extend(normalize_ingress(item) for item in ingresses)
        namespaces = sorted({item.namespace for item in resources if item.namespace})
        for namespace in namespaces:
            scoped = [item for item in resources if item.namespace == namespace]
            resources.append(
                NormalizedResource(
                    resource_type="namespace",
                    name=namespace,
                    namespace=namespace,
                    status=worst(*(item.status for item in scoped)) if scoped else "UNKNOWN",
                    summary=f"{len(scoped)} resources",
                    check_type="POD_STATUS",
                )
            )
        snapshot = snapshot_from_resources(
            resources,
            cluster_arn=cluster.arn,
            control_plane_status=cluster.cluster_status,
        )
        return snapshot, resources


# Backwards-compatible alias used by AWS tests and collectors.
DefaultKubernetesCollector = SharedKubernetesCollector
