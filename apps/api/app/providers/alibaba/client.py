from __future__ import annotations

from typing import Any

from app.providers.alibaba.auth import _openapi_config, assume_role, load_static_keys
from app.providers.alibaba.exceptions import AlibabaAuthError, classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_map"):
        return value.to_map() or {}
    payload: dict[str, Any] = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        item = getattr(value, key)
        if callable(item):
            continue
        payload[key] = item
    return payload


class AlibabaClientFactory:
    def __init__(self, config: AlibabaConnectionConfig) -> None:
        self._config = config
        self._creds: tuple[str, str, str] | None = None

    def credentials(self) -> tuple[str, str, str]:
        if self._creds is None:
            access_key_id, access_key_secret = load_static_keys(self._config)
            self._creds = assume_role(self._config, access_key_id, access_key_secret)
        return self._creds

    def _config_for(self, endpoint: str):
        access_key_id, access_key_secret, token = self.credentials()
        return _openapi_config(
            access_key_id, access_key_secret, self._config.cloud_region, endpoint, token or None
        )

    def cs_client(self):
        try:
            from alibabacloud_cs20151215.client import Client as CSClient
        except ImportError as error:
            raise AlibabaAuthError("Alibaba Container Service SDK is not installed") from error
        return CSClient(self._config_for("cs.aliyuncs.com"))

    def cas_client(self):
        try:
            from alibabacloud_cas20200407.client import Client as CasClient
        except ImportError as error:
            raise AlibabaAuthError("Alibaba Certificate SDK is not installed") from error
        return CasClient(self._config_for("cas.aliyuncs.com"))

    def list_clusters(self) -> list[dict[str, Any]]:
        try:
            from alibabacloud_cs20151215 import models as cs_models

            response = self.cs_client().describe_clusters_v1(cs_models.DescribeClustersV1Request())
        except Exception as error:
            raise classify_alibaba_error(error) from error
        body = _as_dict(getattr(response, "body", response))
        clusters = (
            body.get("clusters")
            or body.get("Clusters")
            or body.get("cluster_list")
            or []
        )
        return [_as_dict(item) for item in clusters]

    def describe_cluster(self, cluster_id: str) -> dict[str, Any]:
        try:
            from alibabacloud_cs20151215 import models as cs_models

            response = self.cs_client().describe_cluster_detail(
                cluster_id, cs_models.DescribeClusterDetailRequest()
            )
        except TypeError:
            try:
                response = self.cs_client().describe_cluster_detail(cluster_id)
            except Exception as error:
                raise classify_alibaba_error(error) from error
        except Exception as error:
            raise classify_alibaba_error(error) from error
        return _as_dict(getattr(response, "body", response))

    def describe_kubeconfig(self, cluster_id: str) -> dict[str, Any]:
        try:
            from alibabacloud_cs20151215 import models as cs_models

            request = cs_models.DescribeClusterUserKubeconfigRequest(private_ip_address=False)
            response = self.cs_client().describe_cluster_user_kubeconfig(cluster_id, request)
        except Exception as error:
            raise classify_alibaba_error(error) from error
        return _as_dict(getattr(response, "body", response))

    def list_user_certificates(self) -> list[dict[str, Any]]:
        try:
            from alibabacloud_cas20200407 import models as cas_models

            request = cas_models.ListUserCertificateOrderRequest(order_type="CERT", show_size=50, current_page=1)
            response = self.cas_client().list_user_certificate_order(request)
        except Exception as error:
            raise classify_alibaba_error(error) from error
        body = _as_dict(getattr(response, "body", response))
        items = (
            body.get("certificate_order_list")
            or body.get("CertificateOrderList")
            or body.get("certificateOrderList")
            or body.get("certificate_list")
            or body.get("certificates")
            or []
        )
        return [_as_dict(item) for item in items]
