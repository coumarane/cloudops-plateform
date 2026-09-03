from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models import (
    CloudAccountRow,
    CloudEnvironmentRow,
    EksClusterRow,
    ManagedProviderRow,
)
from app.db.session import SessionLocal
from app.main import app
from app.providers.contract import ConnectionValidation
from app.core.security import contains_secret_value, walk_strings

client = TestClient(app)


def _real_mode(monkeypatch, *, stub: bool = True) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "seed_topology", False)
    monkeypatch.setattr(settings, "provider_stub", stub)
    monkeypatch.setattr(settings, "app_environment", "development")
    monkeypatch.setattr(settings, "bootstrap_admin_enabled", False)
    monkeypatch.setattr(settings, "celery_eager", True)


def _wipe() -> None:
    session = SessionLocal()
    session.query(EksClusterRow).delete()
    session.query(CloudEnvironmentRow).delete()
    session.query(CloudAccountRow).delete()
    session.query(ManagedProviderRow).delete()
    session.commit()
    session.close()


def _onboard_aws() -> dict[str, str]:
    provider = client.post(
        "/api/v1/providers",
        json={"providerType": "AWS", "name": "AWS Corporate", "description": "corp", "enabled": True, "authStrategy": "AssumeRole"},
    )
    assert provider.status_code == 200, provider.text
    provider_id = provider.json()["id"]
    credential = client.post(
        "/api/v1/credentials",
        json={
            "name": "aws-emea-identity",
            "provider": "aws",
            "region": "emea",
            "account": "aws-emea-nonprod",
            "environment": "dev",
            "credentialType": "sts_assume_role",
            "roleArn": "arn:aws:iam::123456789012:role/CloudOpsDiscoveryRole",
        },
    )
    assert credential.status_code == 200, credential.text
    account = client.post(
        "/api/v1/accounts",
        json={
            "providerId": provider_id,
            "name": "AWS EMEA NonProd",
            "accountId": "123456789012",
            "region": "EMEA",
            "cloudRegion": "eu-west-1",
            "roleArn": "arn:aws:iam::123456789012:role/CloudOpsDiscoveryRole",
            "accountClass": "NONPROD",
            "credentialRef": credential.json()["secretReference"] or credential.json()["id"],
            "authStrategy": "AssumeRole",
        },
    )
    assert account.status_code == 200, account.text
    environment = client.post(
        "/api/v1/environments",
        json={"accountId": account.json()["id"], "name": "DEV", "environmentClass": "DEV", "description": "dev"},
    )
    assert environment.status_code == 200, environment.text
    return {
        "providerId": provider_id,
        "accountId": account.json()["id"],
        "environmentId": environment.json()["id"],
        "credentialId": credential.json()["id"],
    }


def test_empty_database_onboarding(monkeypatch) -> None:
    _real_mode(monkeypatch, stub=False)
    _wipe()
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["onboarding"] is True
    assert dashboard["demoMode"] is False
    assert dashboard["matrix"] == []
    assert dashboard["alerts"] == []
    clusters = client.get("/api/v1/clusters").json()["items"]
    assert clusters == []
    providers = client.get("/api/v1/providers").json()["items"]
    assert providers == []
    status = client.get("/api/v1/platform/status").json()
    assert status["onboarding"] is True
    assert status["dataSource"] == "REAL"


def test_demo_mode_disabled_has_no_fake_records(monkeypatch) -> None:
    _real_mode(monkeypatch)
    _wipe()
    for path in ("/api/v1/clusters", "/api/v1/certificates", "/api/v1/applications", "/api/v1/alerts"):
        body = client.get(path).json()
        assert body["items"] == [], path
    names = [item["name"] for item in client.get("/api/v1/clusters").json()["items"]]
    assert "eu-west-1-uat-k8s" not in names


def test_aws_provider_account_environment_validate_and_discover(monkeypatch) -> None:
    _real_mode(monkeypatch)
    _wipe()
    ids = _onboard_aws()
    validated = client.post(f"/api/v1/accounts/{ids['accountId']}/validate")
    assert validated.status_code == 200, validated.text
    body = validated.json()
    assert body["connected"] is True
    assert body["account"] == "123456789012"
    assert body["principal"] == "CloudOpsRole"
    assert "SecretAccessKey" not in str(body)
    assert "sessionToken" not in str(body).lower()
    discovered = client.post(f"/api/v1/environments/{ids['environmentId']}/discover")
    assert discovered.status_code == 200, discovered.text
    assert discovered.json()["jobId"]
    job = client.get(f"/api/v1/discovery-jobs/{discovered.json()['jobId']}")
    assert job.status_code == 200
    assert job.json()["status"] in {"QUEUED", "RUNNING", "SUCCEEDED", "PARTIAL"}
    clusters = client.get("/api/v1/clusters").json()["items"]
    assert clusters
    assert all(item["source"] != "mock" for item in clusters)
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["onboarding"] is False
    assert dashboard["configuredProviders"] >= 1
    certs = client.post(f"/api/v1/environments/{ids['environmentId']}/certificate-scan")
    assert certs.status_code == 200
    health = client.post(f"/api/v1/environments/{ids['environmentId']}/health-scan")
    assert health.status_code == 200
    provider = client.get(f"/api/v1/providers/{ids['providerId']}").json()
    assert provider["accounts"] >= 1
    assert provider["environments"] >= 1


def test_alibaba_provider_setup(monkeypatch) -> None:
    _real_mode(monkeypatch)
    _wipe()
    provider = client.post(
        "/api/v1/providers",
        json={"providerType": "Alibaba", "name": "Alibaba China", "enabled": True, "authStrategy": "RAM"},
    )
    assert provider.status_code == 200, provider.text
    account = client.post(
        "/api/v1/accounts",
        json={
            "providerId": provider.json()["id"],
            "name": "Alibaba China NonProd",
            "accountId": "123456789012",
            "region": "China",
            "cloudRegion": "cn-hangzhou",
            "ramRole": "acs:ram::123456789012:role/CloudOpsDiscoveryRole",
            "accountClass": "NONPROD",
            "authStrategy": "RAM",
        },
    )
    assert account.status_code == 200, account.text
    environment = client.post(
        "/api/v1/environments",
        json={"accountId": account.json()["id"], "name": "DEV", "environmentClass": "DEV"},
    )
    assert environment.status_code == 200, environment.text
    validated = client.post(f"/api/v1/accounts/{account.json()['id']}/validate")
    assert validated.status_code == 200, validated.text
    assert validated.json()["connected"] is True
    discovered = client.post(f"/api/v1/environments/{environment.json()['id']}/discover")
    assert discovered.status_code == 200
    clusters = client.get("/api/v1/clusters").json()["items"]
    assert any(item["provider"] == "Alibaba" for item in clusters)


def test_failed_validation(monkeypatch) -> None:
    _real_mode(monkeypatch, stub=False)
    _wipe()
    ids = _onboard_aws()

    class Broken:
        discovery_job_kind = "aws-cluster-discovery"
        health_job_kind = "aws-health-scan"
        certificate_job_kind = "aws-certificate-scan"

        def validate_connection(self, account):
            return ConnectionValidation(connected=False, error_category="AccessDenied", detail="role denied")

    with patch("app.platform.service.provider_adapter", return_value=Broken()):
        result = client.post(f"/api/v1/accounts/{ids['accountId']}/validate")
    assert result.status_code == 200
    assert result.json()["connected"] is False
    account = client.get(f"/api/v1/accounts/{ids['accountId']}").json()
    assert account["readiness"] == "VALIDATION_FAILED"


def test_credential_reference_never_returns_secret(monkeypatch) -> None:
    _real_mode(monkeypatch)
    _wipe()
    created = client.post(
        "/api/v1/credentials",
        json={
            "name": "access-key-ref",
            "provider": "aws",
            "region": "emea",
            "account": "aws-emea-nonprod",
            "environment": "dev",
            "credentialType": "access_key",
            "secretValue": '{"AccessKeyId":"AKIAIOSFODNN7EXAMPLE","SecretAccessKey":"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}',
        },
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert "secretValue" not in payload
    assert "wJalrXUtnFEMI" not in str(payload)
    for value in walk_strings(payload):
        assert contains_secret_value(value) is False


def test_application_and_settings_crud(monkeypatch) -> None:
    _real_mode(monkeypatch)
    _wipe()
    ids = _onboard_aws()
    created = client.post(
        "/api/v1/applications",
        json={
            "name": "payments-api",
            "ownerTeam": "payments",
            "repositoryId": "org/payments",
            "pipelineId": "pipe-1",
            "environments": [
                {
                    "environmentId": ids["environmentId"],
                    "clusterId": "cluster-1",
                    "namespace": "payments",
                    "workload": "payments-api",
                    "healthEndpoint": "https://payments.example/health",
                }
            ],
        },
    )
    assert created.status_code == 200, created.text
    updated = client.put(
        f"/api/v1/applications/{created.json()['id']}",
        json={"description": "core payments"},
    )
    assert updated.status_code == 200
    settings_resp = client.put("/api/v1/platform/settings", json={"values": {"discovery_interval_seconds": "1800"}})
    assert settings_resp.status_code == 200
    listed = client.get("/api/v1/platform/settings").json()["items"]
    assert any(item["key"] == "discovery_interval_seconds" and item["value"] == "1800" for item in listed)


def test_bootstrap_admin_disabled_outside_local(monkeypatch) -> None:
    _real_mode(monkeypatch)
    monkeypatch.setattr(settings, "app_environment", "production")
    monkeypatch.setattr(settings, "bootstrap_admin_enabled", False)
    denied = client.post("/api/v1/providers", json={"providerType": "AWS", "name": "blocked"})
    assert denied.status_code == 403


def test_github_integration_write_only_secret(monkeypatch) -> None:
    _real_mode(monkeypatch)
    created = client.post(
        "/api/v1/admin/integrations/github",
        json={"appId": "1", "installationId": "2", "organization": "acme", "privateKey": "-----BEGIN PRIVATE KEY-----\nMIIB\n-----END PRIVATE KEY-----"},
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert "privateKey" not in payload
    assert "BEGIN PRIVATE KEY" not in str(payload)
    validated = client.post(f"/api/v1/admin/integrations/github/{payload['id']}/validate")
    assert validated.status_code == 200
    assert validated.json()["connected"] is True
