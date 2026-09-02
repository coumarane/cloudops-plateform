from __future__ import annotations

import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from botocore.signers import RequestSigner

from app.core.logging import get_logger
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.errors import AwsTransientError, classify_aws_error
from app.providers.aws.models import ClusterHealthSnapshot, DiscoveredCluster
from app.providers.kubernetes.collector import DefaultKubernetesCollector, KubernetesCollector

logger = get_logger(__name__)


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
