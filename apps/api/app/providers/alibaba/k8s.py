from __future__ import annotations

import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.providers.alibaba.client import AlibabaClientFactory
from app.providers.alibaba.exceptions import classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig
from app.providers.common.models import ClusterHealthSnapshot, DiscoveredCluster
from app.providers.kubernetes.collector import SharedKubernetesCollector

logger = get_logger(__name__)


def _write_temp(prefix: str, suffix: str, raw: bytes) -> str:
    handle = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
    handle.write(raw)
    handle.close()
    return handle.name


def kubeconfig_auth_material(kubeconfig: dict[str, Any]) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Return endpoint, token, ca_data, cert_data, key_data. Never logs kubeconfig contents."""
    clusters = kubeconfig.get("clusters") or []
    users = kubeconfig.get("users") or []
    endpoint = None
    ca_data = None
    if clusters:
        cluster = (clusters[0] or {}).get("cluster") or {}
        endpoint = cluster.get("server")
        ca_data = cluster.get("certificate-authority-data")
    token = None
    cert_data = None
    key_data = None
    if users:
        user = (users[0] or {}).get("user") or {}
        token = user.get("token")
        cert_data = user.get("client-certificate-data")
        key_data = user.get("client-key-data")
    return str(endpoint or ""), token, ca_data, cert_data, key_data


class AckHealthCollector:
    def __init__(
        self,
        factory: AlibabaClientFactory,
        config: AlibabaConnectionConfig,
        kubernetes: SharedKubernetesCollector | None = None,
    ) -> None:
        self._factory = factory
        self._config = config
        self._kubernetes = kubernetes or SharedKubernetesCollector()

    def collect(self, cluster: DiscoveredCluster) -> ClusterHealthSnapshot:
        now = datetime.now(timezone.utc)
        if cluster.cluster_status not in {"ACTIVE"}:
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="ACK control plane is not ACTIVE",
            )
        cluster_id = ""
        try:
            import json

            extra = json.loads(cluster.extra_json or "{}")
            cluster_id = str(extra.get("cluster_id") or "")
        except Exception:
            cluster_id = ""
        if not cluster_id and cluster.arn:
            cluster_id = cluster.arn.rsplit("/", 1)[-1]
        temps: list[str] = []
        try:
            payload = self._factory.describe_kubeconfig(cluster_id)
            kubeconfig_yaml = payload.get("config") or payload.get("kubeconfig") or ""
            if not kubeconfig_yaml:
                return ClusterHealthSnapshot(
                    cluster_arn=cluster.arn,
                    control_plane_status=cluster.cluster_status,
                    kubernetes_api_reachable=False,
                    last_checked=now,
                    detail="ACK kubeconfig was not returned",
                )
            import yaml

            kubeconfig = yaml.safe_load(kubeconfig_yaml) if isinstance(kubeconfig_yaml, str) else kubeconfig_yaml
            if not isinstance(kubeconfig, dict):
                raise ValueError("kubeconfig")
            endpoint, token, ca_data, cert_data, key_data = kubeconfig_auth_material(kubeconfig)
            cluster.endpoint = cluster.endpoint or endpoint
            ca_path = ""
            cert_path = ""
            key_path = ""
            if ca_data:
                ca_path = _write_temp("ack-ca-", ".crt", base64.b64decode(ca_data))
                temps.append(ca_path)
            if cert_data:
                cert_path = _write_temp("ack-cert-", ".crt", base64.b64decode(cert_data))
                temps.append(cert_path)
            if key_data:
                key_path = _write_temp("ack-key-", ".key", base64.b64decode(key_data))
                temps.append(key_path)
            return self._kubernetes.collect(
                cluster,
                token or "",
                ca_path,
                cert_path=cert_path,
                key_path=key_path,
            )
        except Exception as error:
            mapped = classify_alibaba_error(error)
            logger.warning("ACK health collection failed cluster=%s error=%s", cluster.name, mapped)
            return ClusterHealthSnapshot(
                cluster_arn=cluster.arn,
                control_plane_status=cluster.cluster_status,
                kubernetes_api_reachable=False,
                last_checked=now,
                detail="Unable to authenticate to the Kubernetes API",
            )
        finally:
            for path in temps:
                Path(path).unlink(missing_ok=True)
