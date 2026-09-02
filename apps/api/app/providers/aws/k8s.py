from __future__ import annotations

import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from botocore.signers import RequestSigner

from app.core.logging import get_logger
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.errors import AwsTransientError, classify_aws_error
from app.providers.aws.models import ClusterHealthSnapshot, DiscoveredCluster

logger = get_logger(__name__)


class KubernetesCollector(Protocol):
    def collect(self, cluster: DiscoveredCluster, token: str, ca_path: str) -> ClusterHealthSnapshot: ...


def eks_bearer_token(factory: AwsClientFactory, cluster_name: str, region: str) -> str:
    session = factory.session
    credentials = session.get_credentials()
    if credentials is None:
        raise AwsTransientError("AWS credentials are unavailable for EKS token signing")
    signer = RequestSigner(
        "sts",
        region,
        "sts",
        "v4",
        credentials,
        session.events,
    )
    params = {
        "method": "GET",
        "url": f"https://sts.{region}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
        "body": {},
        "headers": {"x-k8s-aws-id": cluster_name},
        "context": {},
    }
    signed_url = signer.generate_presigned_url(
        params,
        region_name=region,
        expires_in=60,
        operation_name="",
    )
    encoded = base64.urlsafe_b64encode(signed_url.encode("utf-8")).decode("utf-8").rstrip("=")
    return f"k8s-aws-v1.{encoded}"


class DefaultKubernetesCollector:
    def collect(self, cluster: DiscoveredCluster, token: str, ca_path: str) -> ClusterHealthSnapshot:
        now = datetime.now(timezone.utc)
        if not cluster.endpoint:
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="Cluster API endpoint was not returned by EKS",
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
        configuration.ssl_ca_cert = ca_path
        configuration.api_key = {"authorization": f"Bearer {token}"}
        api_client = client.ApiClient(configuration)
        core = client.CoreV1Api(api_client)
        apps = client.AppsV1Api(api_client)
        batch = client.BatchV1Api(api_client)
        try:
            nodes = core.list_node().items
            pods = core.list_pod_for_all_namespaces().items
            deployments = apps.list_deployment_for_all_namespaces().items
            jobs = batch.list_job_for_all_namespaces().items
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
        return ClusterHealthSnapshot(
            cluster_arn=cluster.arn,
            control_plane_status=cluster.cluster_status,
            kubernetes_api_reachable=True,
            node_count=len(nodes),
            ready_node_count=ready_nodes,
            pod_count=len(pods),
            unhealthy_pod_count=unhealthy,
            crashloop_backoff_count=crashloop,
            pending_pod_count=pending,
            unavailable_deployment_count=unavailable,
            failed_job_count=failed_jobs,
            last_checked=now,
        )


class ClusterHealthCollector:
    def __init__(
        self,
        factory: AwsClientFactory | None = None,
        kubernetes: KubernetesCollector | None = None,
    ) -> None:
        self._factory = factory or AwsClientFactory()
        self._kubernetes = kubernetes or DefaultKubernetesCollector()

    def collect(self, cluster: DiscoveredCluster, ca_data: str | None = None) -> ClusterHealthSnapshot:
        now = datetime.now(timezone.utc)
        if cluster.cluster_status not in {"ACTIVE"}:
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="EKS control plane is not ACTIVE",
            )
        try:
            token = eks_bearer_token(self._factory, cluster.name, cluster.cloud_region)
        except Exception as error:
            mapped = classify_aws_error(error)
            logger.warning("Unable to mint EKS token cluster=%s error=%s", cluster.name, mapped)
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="Unable to authenticate to the Kubernetes API",
            )
        ca_path = None
        try:
            if ca_data:
                raw = base64.b64decode(ca_data)
                handle = tempfile.NamedTemporaryFile(prefix="eks-ca-", suffix=".crt", delete=False)
                handle.write(raw)
                handle.close()
                ca_path = handle.name
            return self._kubernetes.collect(cluster, token, ca_path or "")
        finally:
            if ca_path:
                Path(ca_path).unlink(missing_ok=True)
