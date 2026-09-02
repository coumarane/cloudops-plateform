from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.alibaba.ack import AckDiscovery, environment_from_tags, normalize_ack_cluster
from app.providers.alibaba.adapter import AlibabaProviderAdapter
from app.providers.alibaba.auth import fingerprint_access_key_id, get_caller_identity, load_static_keys
from app.providers.alibaba.certificates import normalize_cas_certificate, normalize_tls_secret
from app.providers.alibaba.exceptions import AlibabaAuthError, AlibabaPermissionError, AlibabaTransientError, classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig
from app.providers.aws.adapter import AWSProviderAdapter
from app.providers.common.certificates import classify_certificate_age
from app.providers.factory import list_providers, provider_adapter
from app.providers.kubernetes.collector import SharedKubernetesCollector, summarize_workload
from app.topology.alibaba import load_alibaba_topology

client = TestClient(app)


def _config() -> AlibabaConnectionConfig:
    return AlibabaConnectionConfig(
        cloud_region="cn-hangzhou",
        account_id="1234567890",
        role_arn="acs:ram::1234567890:role/CloudOpsInventoryReadOnly",
        session_name="cloudops-alibaba",
        access_key_id_ref="CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_ID",
        access_key_secret_ref="CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET",
        credential_ref="env:CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET",
        platform_region="China",
        environment="DEV",
        account_alias="alibaba-china-nonprod",
        cluster_environment_tag="Environment",
    )


def _ack_payload() -> dict:
    return {
        "cluster_id": "c-ack-dev",
        "name": "platform-ack-dev",
        "region_id": "cn-hangzhou",
        "state": "running",
        "cluster_type": "ManagedKubernetes",
        "current_version": "1.30.1-aliyun.1",
        "created": "2026-01-01T00:00:00Z",
        "master_url": '{"api_server_endpoint":"https://ack.example.cn-hangzhou.aliyuncs.com"}',
        "tags": [{"key": "Environment", "value": "DEV"}],
    }


def test_alibaba_topology_and_prd_readonly() -> None:
    topology = load_alibaba_topology()
    assert {account.alias for account in topology.accounts} == {"alibaba-china-nonprod", "alibaba-china-prod"}
    prod = topology.account_by_alias("alibaba-china-prod")
    assert prod is not None
    assert prod.readonly is True
    prd = client.get("/api/v1/environments/alibaba/china/prd").json()
    assert prd["identity"]["readonly"] is True
    assert prd["identity"]["account"] == "alibaba-china-prod"
    dev = client.get("/api/v1/environments/alibaba/china/dev").json()
    assert dev["identity"]["readonly"] is False
    assert dev["identity"]["account"] == "alibaba-china-nonprod"


def test_provider_factory_returns_both_adapters() -> None:
    assert set(list_providers()) == {"AWS", "Alibaba"}
    assert isinstance(provider_adapter("Alibaba"), AlibabaProviderAdapter)
    assert isinstance(provider_adapter("AWS"), AWSProviderAdapter)
    assert provider_adapter("Alibaba").name == "Alibaba"
    assert provider_adapter("AWS").name == "AWS"


def test_fingerprint_does_not_include_secret() -> None:
    digest = fingerprint_access_key_id("LTAIexamplekeyid")
    assert digest == fingerprint_access_key_id("LTAIexamplekeyid")
    assert "LTAI" not in digest
    assert "secret" not in digest


def test_auth_adapter_requires_env_refs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET", raising=False)
    with pytest.raises(AlibabaAuthError):
        load_static_keys(_config())


def test_auth_adapter_loads_env_refs_without_storing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_ID", "LTAIexamplekeyid")
    monkeypatch.setenv("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET", "super-secret-value")
    key_id, secret = load_static_keys(_config())
    assert key_id == "LTAIexamplekeyid"
    assert secret == "super-secret-value"
    accounts = client.get("/api/v1/accounts", params={"provider": "alibaba"}).json()["items"]
    blob = str(accounts).lower()
    assert "super-secret-value" not in blob
    assert "access_key_secret" not in blob


def test_auth_adapter_get_caller_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    monkeypatch.setenv("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_ID", "LTAIexamplekeyid")
    monkeypatch.setenv("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET", "super-secret-value")

    class FakeBody:
        account_id = "1234567890"
        arn = "acs:ram::1234567890:assumed-role/CloudOpsInventoryReadOnly/cloudops"

    class FakeClient:
        def __init__(self, _config) -> None:
            pass

        def get_caller_identity(self, _request):
            return type("R", (), {"body": FakeBody()})()

    sts_pkg = types.ModuleType("alibabacloud_sts20150401")
    sts_client = types.ModuleType("alibabacloud_sts20150401.client")
    sts_models = types.ModuleType("alibabacloud_sts20150401.models")
    sts_client.Client = FakeClient
    sts_models.GetCallerIdentityRequest = lambda: object()
    sts_pkg.client = sts_client
    sts_pkg.models = sts_models

    with (
        patch("app.providers.alibaba.auth.assume_role", return_value=("tmp-id", "tmp-secret", "tmp-token")),
        patch("app.providers.alibaba.auth._openapi_config", return_value=object()),
        patch.dict(
            sys.modules,
            {
                "alibabacloud_sts20150401": sts_pkg,
                "alibabacloud_sts20150401.client": sts_client,
                "alibabacloud_sts20150401.models": sts_models,
            },
        ),
    ):
        identity = get_caller_identity(_config())
    assert identity.account_id == "1234567890"
    assert identity.fingerprint == fingerprint_access_key_id("LTAIexamplekeyid")
    assert identity.status == "ok"


def test_ack_normalization_maps_tst_to_int_tst() -> None:
    assert environment_from_tags([{"key": "Environment", "value": "TST"}], "Environment") == "INT/TST"
    cluster = normalize_ack_cluster(_ack_payload(), _config(), ("DEV", "INT/TST", "UAT"))
    assert cluster is not None
    assert cluster.provider == "Alibaba"
    assert cluster.cluster_status == "ACTIVE"
    assert cluster.environment == "DEV"
    assert cluster.endpoint.startswith("https://")
    assert "token" not in cluster.extra_json
    assert '"cluster_id": "c-ack-dev"' in cluster.extra_json or "c-ack-dev" in cluster.extra_json


def test_ack_discovery_normalizes_mocked_sdk_dicts() -> None:
    factory = MagicMock()
    factory.list_clusters.return_value = [_ack_payload()]
    factory.describe_cluster.return_value = {"current_version": "1.30.1-aliyun.1"}
    clusters = AckDiscovery(factory, _config()).list_clusters(("DEV", "INT/TST", "UAT"))
    assert len(clusters) == 1
    assert clusters[0].name == "platform-ack-dev"
    assert clusters[0].provider == "Alibaba"
    factory.describe_cluster.assert_called_once_with("c-ack-dev")


def test_certificate_classification_buckets() -> None:
    assert classify_certificate_age(90) == ("OK", "Healthy")
    assert classify_certificate_age(45) == ("Expiring", "Warning")
    assert classify_certificate_age(20) == ("Expiring", "Critical")
    assert classify_certificate_age(3) == ("Expiring", "Urgent")
    assert classify_certificate_age(-1) == ("Expired", "Expired")
    cert = normalize_cas_certificate(
        {
            "certificate_id": "cert-1",
            "domain": "dev.china.example.com",
            "end_date": "2026-12-01",
            "start_date": "2026-01-01",
            "issuer": "Aliyun",
        },
        _config(),
        now=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert cert.provider == "Alibaba"
    assert cert.source == "cas"
    assert cert.days_remaining == 183
    assert "pem" not in cert.arn


def test_tls_secret_normalization_ignores_private_key() -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import base64

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "tls.dev.china.example.com")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime(2026, 1, 1, tzinfo=timezone.utc))
        .not_valid_after(datetime(2026, 12, 1, tzinfo=timezone.utc))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("tls.dev.china.example.com")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    pem = cert.public_bytes(serialization.Encoding.PEM)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    parsed = normalize_tls_secret(
        {
            "metadata": {"name": "ingress-tls", "namespace": "platform"},
            "data": {
                "tls.crt": base64.b64encode(pem).decode("ascii"),
                "tls.key": base64.b64encode(private_pem).decode("ascii"),
            },
            "type": "kubernetes.io/tls",
        },
        _config(),
        cluster_name="platform-ack-dev",
        now=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert parsed is not None
    assert parsed.source == "kubernetes"
    assert parsed.namespace == "platform"
    assert parsed.cluster_name == "platform-ack-dev"
    assert "BEGIN PRIVATE KEY" not in parsed.arn
    assert "tls.key" not in parsed.arn
    assert parsed.days_remaining == 183


def test_shared_kubernetes_health_normalization() -> None:
    cluster = normalize_ack_cluster(_ack_payload(), _config(), ("DEV",))
    assert cluster is not None
    snapshot = summarize_workload(
        node_count=3,
        ready_node_count=3,
        pod_count=10,
        unhealthy_pod_count=1,
        crashloop_backoff_count=1,
        pending_pod_count=0,
        unavailable_deployment_count=0,
        failed_job_count=0,
        stateful_set_unhealthy_count=1,
        ingress_unhealthy_count=2,
        cluster=cluster,
    )
    assert snapshot.kubernetes_api_reachable is True
    assert snapshot.node_count == 3
    assert snapshot.crashloop_backoff_count == 1
    assert snapshot.stateful_set_unhealthy_count == 1
    assert snapshot.ingress_unhealthy_count == 2
    cluster.endpoint = None
    unreachable = SharedKubernetesCollector().collect(cluster, "token-must-not-leak", "")
    assert unreachable.kubernetes_api_reachable is False
    assert "token-must-not-leak" not in unreachable.detail


def test_classify_alibaba_errors() -> None:
    assert isinstance(classify_alibaba_error(RuntimeError("Throttling.User")), AlibabaTransientError)
    assert isinstance(classify_alibaba_error(RuntimeError("Forbidden.RAM")), AlibabaPermissionError)
    assert isinstance(classify_alibaba_error(RuntimeError("InvalidAccessKeyId")), AlibabaAuthError)


def test_alibaba_discovery_overlays_china_dev() -> None:
    cluster = normalize_ack_cluster(_ack_payload(), _config(), ("DEV", "INT/TST", "UAT"))

    def discovery(factory, config):
        mock = MagicMock()
        if config.account_alias == "alibaba-china-nonprod":
            mock.list_clusters.return_value = [cluster]
        else:
            mock.list_clusters.return_value = []
        return mock

    with patch("app.providers.alibaba.adapter.AckDiscovery", side_effect=discovery):
        response = client.post("/api/v1/jobs/alibaba/cluster-discovery")
    assert response.status_code == 200
    body = client.get("/api/v1/clusters", params={"provider": "alibaba", "region": "china", "environment": "dev"}).json()["items"]
    assert {item["name"] for item in body} == {"platform-ack-dev"}
    assert all(item["source"] == "alibaba" for item in body)
    assert all(item["provider"] == "Alibaba" for item in body)
    assert all(item["platform"] == "ACK" for item in body)
    aws = client.get("/api/v1/clusters", params={"provider": "aws", "region": "emea", "environment": "dev"}).json()["items"]
    assert any(item["name"] == "eu-west-1-dev-k8s" for item in aws)
    jobs = client.get("/api/v1/jobs", params={"provider": "alibaba"}).json()["items"]
    assert any(item["kind"] == "alibaba-cluster-discovery" for item in jobs)
    assert all(item["provider"] == "Alibaba" for item in jobs if item.get("kind", "").startswith("alibaba-"))


def test_alibaba_partial_failure_does_not_stop_other_account() -> None:
    cluster = normalize_ack_cluster(_ack_payload(), _config(), ("DEV",))

    def discovery(factory, config):
        mock = MagicMock()
        if config.account_alias == "alibaba-china-prod":
            mock.list_clusters.side_effect = AlibabaAuthError("prod unavailable")
        else:
            mock.list_clusters.return_value = [cluster]
        return mock

    with patch("app.providers.alibaba.adapter.AckDiscovery", side_effect=discovery):
        response = client.post("/api/v1/jobs/alibaba/cluster-discovery")
    assert response.status_code == 200
    assert response.json()["result"] == "Succeeded"
    china_dev = client.get("/api/v1/environments/alibaba/china/dev").json()
    assert china_dev["identity"]["discoveryActive"] is True
    china_prd = client.get("/api/v1/environments/alibaba/china/prd").json()
    assert china_prd["identity"]["discoveryActive"] is False
    assert "prod unavailable" in (china_prd["identity"]["lastError"] or "")
    dashboard = client.get("/api/v1/dashboard").json()
    china = next(row for row in dashboard["matrix"] if row["provider"] == "Alibaba")
    assert china["cells"]["DEV"]["live"] is True
    assert china["cells"]["PRD"]["readonly"] is True


def test_alibaba_missing_credentials_fail_sanitized() -> None:
    with patch("app.providers.alibaba.adapter.AckDiscovery") as discovery:
        discovery.return_value.list_clusters.side_effect = AlibabaAuthError(
            "Alibaba credentials were not found or were incomplete"
        )
        response = client.post("/api/v1/jobs/alibaba/cluster-discovery")
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "Failed"
    blob = str(body).lower()
    assert "ltai" not in blob
    assert "access_key_secret" not in blob
    assert "session_token" not in blob
