from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.core.logging import sanitize_text
from app.core.rbac import Principal, ROLE_PERMISSIONS
from app.core.security import contains_secret_value, walk_strings
from app.db.models import CredentialRow
from app.db.session import SessionLocal, engine
from app.main import app
from app.secrets.backends.alibaba import AlibabaSecretsBackend
from app.secrets.backends.aws import AwsSecretsManagerBackend
from app.secrets.backends.local import LocalDevSecretBackend, LocalSecretBackendError
from app.secrets.factory import secret_backend
from app.secrets.fingerprint import fingerprint_secret
from app.services.credentials import compute_status, scan_rotation_statuses

client = TestClient(app)

AWS_SECRET = '{"AccessKeyId":"AKIAIOSFODNN7EXAMPLE","SecretAccessKey":"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}'
ALIBABA_SECRET = '{"AccessKeyId":"LTAI5tExampleKey99","AccessKeySecret":"alibaba-secret-phase6-value-xyz"}'
PLAINTEXT_MARKERS = (
    "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "alibaba-secret-phase6-value-xyz",
    "AKIAIOSFODNN7EXAMPLE",
)


class FakeSecretsManager:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.exceptions = SimpleNamespace(ResourceExistsException=type("ResourceExistsException", (Exception,), {}))

    def create_secret(self, Name: str, SecretString: str) -> dict:
        if Name in self.values:
            raise self.exceptions.ResourceExistsException()
        self.values[Name] = SecretString
        return {"ARN": Name, "Name": Name}

    def put_secret_value(self, SecretId: str, SecretString: str) -> dict:
        self.values[SecretId] = SecretString
        return {"ARN": SecretId}

    def describe_secret(self, SecretId: str) -> dict:
        if SecretId not in self.values:
            raise KeyError(SecretId)
        return {"ARN": SecretId, "Name": SecretId, "VersionIdsToStages": {"v1": ["AWSCURRENT"]}}

    def delete_secret(self, SecretId: str, ForceDeleteWithoutRecovery: bool = True) -> None:
        self.values.pop(SecretId, None)

    def get_secret_value(self, SecretId: str) -> dict:
        return {"SecretString": self.values[SecretId]}


class FakeAlibabaKms:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get_metadata(self, reference: str):
        from app.secrets.backends.base import SecretMetadata

        if reference not in self.values:
            raise KeyError(reference)
        return SecretMetadata(reference=reference, backend="alibaba")

    def store_secret(self, reference: str, secret: str) -> None:
        if reference in self.values:
            raise RuntimeError("exists")
        self.values[reference] = secret

    def replace_secret(self, reference: str, secret: str) -> None:
        self.values[reference] = secret

    def delete_secret_reference(self, reference: str) -> None:
        self.values.pop(reference, None)

    def get_secret(self, reference: str) -> str:
        return self.values[reference]


def _headers(role: str = "PlatformAdmin", user: str = "ops@cloudops.local") -> dict[str, str]:
    return {"X-CloudOps-User": user, "X-CloudOps-Role": role}


def _create_aws(secret: str = AWS_SECRET, **overrides) -> dict:
    payload = {
        "name": "emea-dev-app-runtime",
        "provider": "aws",
        "region": "emea",
        "account": "aws-emea-nonprod",
        "environment": "dev",
        "credentialType": "access_key",
        "secretBackend": "local",
        "secretValue": secret,
        "accountId": "111122223333",
        "rotationPolicyDays": 90,
    }
    payload.update(overrides)
    return client.post("/api/v1/credentials", json=payload, headers=_headers()).json()


def _create_alibaba(secret: str = ALIBABA_SECRET, **overrides) -> dict:
    payload = {
        "name": "china-dev-ack-runtime",
        "provider": "alibaba",
        "region": "china",
        "account": "alibaba-china-nonprod",
        "environment": "dev",
        "credentialType": "access_key",
        "secretBackend": "local",
        "secretValue": secret,
        "accountId": "1234567890",
        "rotationPolicyDays": 90,
    }
    payload.update(overrides)
    return client.post("/api/v1/credentials", json=payload, headers=_headers()).json()


def _all_db_text() -> str:
    session = SessionLocal()
    try:
        chunks: list[str] = []
        for table in inspect(engine).get_table_names():
            rows = session.execute(text(f"SELECT * FROM {table}")).mappings().all()
            chunks.append(str(rows))
        return "\n".join(chunks)
    finally:
        session.close()


def test_local_secret_backend_does_not_use_postgres() -> None:
    backend = LocalDevSecretBackend()
    meta = backend.store_secret("cloudops/test", AWS_SECRET)
    assert backend.validate_reference(meta.reference)
    assert backend.get_secret(meta.reference) == AWS_SECRET
    backend.replace_secret(meta.reference, ALIBABA_SECRET)
    assert AWS_SECRET not in _all_db_text()
    inspector = inspect(engine)
    cred_cols = {col["name"] for col in inspector.get_columns("credentials")}
    assert "secret_value" not in cred_cols
    assert "secret" not in cred_cols


def test_local_backend_disabled_outside_dev() -> None:
    try:
        LocalDevSecretBackend(allow=False)
        raise AssertionError("expected LocalSecretBackendError")
    except LocalSecretBackendError:
        pass


def test_aws_secret_backend_with_fake_client() -> None:
    fake = FakeSecretsManager()
    backend = AwsSecretsManagerBackend(region="eu-west-1", client=fake)
    meta = backend.store_secret("cloudops/aws/emea/dev/app", AWS_SECRET)
    assert fake.values[meta.reference] == AWS_SECRET
    backend.replace_secret(meta.reference, ALIBABA_SECRET)
    assert backend.get_secret(meta.reference) == ALIBABA_SECRET
    assert backend.validate_reference(meta.reference)
    backend.delete_secret_reference(meta.reference)
    assert backend.validate_reference(meta.reference) is False


def test_alibaba_secret_backend_with_fake_client() -> None:
    fake = FakeAlibabaKms()
    backend = AlibabaSecretsBackend(region="cn-hangzhou", client=fake)
    meta = backend.store_secret("cloudops/alibaba/china/dev/app", ALIBABA_SECRET)
    assert fake.values[meta.reference] == ALIBABA_SECRET
    backend.replace_secret(meta.reference, AWS_SECRET)
    assert backend.get_secret(meta.reference) == AWS_SECRET
    backend.delete_secret_reference(meta.reference)
    assert backend.validate_reference(meta.reference) is False


def test_factory_returns_named_backends() -> None:
    assert secret_backend("local").name == "local"
    assert secret_backend("aws", region="eu-west-1", client=FakeSecretsManager()).name == "aws"
    assert secret_backend("alibaba", region="cn-hangzhou", client=FakeAlibabaKms()).name == "alibaba"


def test_create_and_replace_never_persist_plaintext() -> None:
    created = _create_aws()
    assert created["id"].startswith("cred-")
    assert "secretValue" not in created
    assert created["fingerprint"] == fingerprint_secret(AWS_SECRET)
    assert created["secretReference"]
    dumped = _all_db_text()
    for marker in PLAINTEXT_MARKERS:
        assert marker not in dumped
    replaced = client.post(
        f"/api/v1/credentials/{created['id']}/replace",
        json={"secretValue": ALIBABA_SECRET.replace("alibaba", "rotated")},
        headers=_headers(),
    )
    assert replaced.status_code == 400
    rotated = '{"AccessKeyId":"AKIAIOSFODNN7EXAMPLE","SecretAccessKey":"rotated-phase6-secret-value-aaaa"}'
    response = client.post(
        f"/api/v1/credentials/{created['id']}/replace",
        json={"secretValue": rotated},
        headers=_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert "secretValue" not in body
    assert body["fingerprint"] != created["fingerprint"]
    dumped = _all_db_text()
    assert "rotated-phase6-secret-value-aaaa" not in dumped
    assert AWS_SECRET not in dumped


def test_api_never_exposes_secret_or_secret_route() -> None:
    created = _create_aws()
    for path in (
        "/api/v1/credentials",
        f"/api/v1/credentials/{created['id']}",
        f"/api/v1/credentials/{created['id']}/history",
        f"/api/v1/credentials/{created['id']}/validations",
        "/api/v1/secrets",
        "/api/v1/audit-events",
    ):
        body = client.get(path, headers=_headers()).json()
        payload = str(body)
        for marker in PLAINTEXT_MARKERS:
            assert marker not in payload
        for value in walk_strings(body):
            assert contains_secret_value(value) is False
    missing = client.get(f"/api/v1/credentials/{created['id']}/secret", headers=_headers())
    assert missing.status_code in {404, 405}
    listed = client.get("/api/v1/credentials", params={"provider": "aws", "region": "emea", "environment": "dev"}).json()
    assert any(item["name"] == "emea-dev-app-runtime" for item in listed["items"])


def test_logs_never_expose_secret(caplog) -> None:
    caplog.set_level(logging.INFO)
    _create_aws()
    joined = "\n".join(record.getMessage() for record in caplog.records)
    for marker in PLAINTEXT_MARKERS:
        assert marker not in joined
    assert "wJalrXUtnFEMI" not in sanitize_text(AWS_SECRET)


def test_audit_record_is_sanitized() -> None:
    created = _create_aws()
    client.post(
        f"/api/v1/credentials/{created['id']}/replace",
        json={
            "secretValue": '{"AccessKeyId":"AKIAIOSFODNN7EXAMPLE","SecretAccessKey":"audit-phase6-secret-value"}',
            "reason": "rotate AccessKeySecret=should-not-appear",
        },
        headers=_headers(),
    )
    events = client.get("/api/v1/audit-events").json()["items"]
    blob = str(events)
    assert "audit-phase6-secret-value" not in blob
    assert "should-not-appear" not in blob
    session = SessionLocal()
    try:
        rows = session.query(CredentialRow).all()
        assert rows
        for row in rows:
            assert row.fingerprint
            assert "audit-phase6-secret-value" not in (row.extra_json or "")
    finally:
        session.close()


def test_alibaba_nonprod_credential_roundtrip() -> None:
    created = _create_alibaba()
    assert created["provider"] == "Alibaba"
    assert created["region"] == "China"
    assert created["environment"] == "DEV"
    assert "secretValue" not in created
    listed = client.get("/api/v1/credentials", params={"provider": "alibaba"}).json()["items"]
    assert any(item["id"] == created["id"] for item in listed)
    secrets = client.get("/api/v1/secrets", params={"provider": "alibaba", "environment": "dev"}).json()["items"]
    live = next(item for item in secrets if item["id"] == created["id"])
    assert live["maskedValue"] == "••••••••••••"
    assert live["source"] == "live"
    assert live["fingerprint"]


@patch("app.services.credential_jobs._validate_aws", return_value="111122223333")
def test_validation_job_stores_result_without_secret(mock_validate) -> None:
    created = _create_aws()
    response = client.post(f"/api/v1/credentials/{created['id']}/validate", headers=_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["queued"] is True
    assert body["status"] in {"queued", "running", "succeeded"}
    assert "secretValue" not in body
    mock_validate.assert_called_once()
    validations = client.get(f"/api/v1/credentials/{created['id']}/validations", headers=_headers()).json()["items"]
    assert validations[0]["success"] is True
    assert validations[0]["providerAccount"] == "111122223333"
    assert "wJalr" not in str(validations)


@patch("app.services.credential_jobs._validate_alibaba", return_value="1234567890")
def test_alibaba_validation_job(mock_validate) -> None:
    created = _create_alibaba()
    response = client.post(f"/api/v1/credentials/{created['id']}/validate", headers=_headers())
    assert response.status_code == 200
    mock_validate.assert_called_once()
    validations = client.get(f"/api/v1/credentials/{created['id']}/validations").json()["items"]
    assert validations[0]["providerAccount"] == "1234567890"


def test_rbac_read_only_cannot_create() -> None:
    response = client.post(
        "/api/v1/credentials",
        json={
            "name": "blocked",
            "provider": "aws",
            "region": "emea",
            "account": "aws-emea-nonprod",
            "environment": "dev",
            "credentialType": "application",
            "secretValue": "app-secret-phase6",
        },
        headers=_headers("ReadOnly"),
    )
    assert response.status_code == 403
    auditor = client.get("/api/v1/credentials", headers=_headers("SecurityAuditor"))
    assert auditor.status_code == 200
    developer = client.post(
        "/api/v1/credentials/cred-missing/validate",
        headers=_headers("Developer"),
    )
    assert developer.status_code == 403
    assert ROLE_PERMISSIONS["PlatformAdmin"] == ROLE_PERMISSIONS["PlatformAdmin"]
    assert "credential:prod_update" not in ROLE_PERMISSIONS["DevOpsEngineer"]
    assert ROLE_PERMISSIONS["Developer"] == frozenset(
        {
            "credential:read",
            "certificate:read",
            "github:read",
            "github_variable:read",
            "github_variable:update",
            "github_secret:read_metadata",
        }
    )


def test_production_replace_requires_permission_confirmation_and_reason() -> None:
    created = client.post(
        "/api/v1/credentials",
        json={
            "name": "prd-payments",
            "provider": "aws",
            "region": "emea",
            "account": "aws-emea-prod",
            "environment": "prd",
            "credentialType": "application",
            "secretValue": "prd-secret-phase6-initial",
            "confirmed": True,
            "reason": "bootstrap",
            "changeTicket": "CHG-1",
        },
        headers=_headers("PlatformAdmin"),
    )
    assert created.status_code == 200, created.text
    credential_id = created.json()["id"]
    denied = client.post(
        f"/api/v1/credentials/{credential_id}/replace",
        json={"secretValue": "prd-secret-phase6-next", "confirmed": True, "reason": "rotate"},
        headers=_headers("DevOpsEngineer"),
    )
    assert denied.status_code == 403
    missing_confirm = client.post(
        f"/api/v1/credentials/{credential_id}/replace",
        json={"secretValue": "prd-secret-phase6-next", "reason": "rotate"},
        headers=_headers("PlatformAdmin"),
    )
    assert missing_confirm.status_code == 400
    missing_reason = client.post(
        f"/api/v1/credentials/{credential_id}/replace",
        json={"secretValue": "prd-secret-phase6-next", "confirmed": True},
        headers=_headers("PlatformAdmin"),
    )
    assert missing_reason.status_code == 400
    allowed = client.post(
        f"/api/v1/credentials/{credential_id}/replace",
        json={
            "secretValue": "prd-secret-phase6-next",
            "confirmed": True,
            "reason": "scheduled replace",
            "changeTicket": "CHG-99",
        },
        headers=_headers("PlatformAdmin"),
    )
    assert allowed.status_code == 200
    assert "prd-secret-phase6-next" not in _all_db_text()
    assert "prd-secret-phase6-next" not in allowed.text


def test_npd_also_requires_prod_permission() -> None:
    created = client.post(
        "/api/v1/credentials",
        json={
            "name": "npd-sync",
            "provider": "aws",
            "region": "emea",
            "account": "aws-emea-prod",
            "environment": "npd",
            "credentialType": "application",
            "secretValue": "npd-secret-phase6",
            "confirmed": True,
            "reason": "bootstrap",
        },
        headers=_headers("DevOpsEngineer"),
    )
    assert created.status_code == 403


def test_role_credential_can_be_metadata_only() -> None:
    response = client.post(
        "/api/v1/credentials",
        json={
            "name": "emea-dev-inventory-role",
            "provider": "aws",
            "region": "emea",
            "account": "aws-emea-nonprod",
            "environment": "dev",
            "credentialType": "iam_role",
            "roleArn": "arn:aws:iam::111122223333:role/CloudOpsInventory",
        },
        headers=_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["roleArn"].endswith("CloudOpsInventory")
    assert body["fingerprint"] == ""


def test_rotation_status_scan_updates_due_and_overdue() -> None:
    created = _create_aws(rotationPolicyDays=90)
    session = SessionLocal()
    try:
        row = session.get(CredentialRow, created["id"])
        assert row is not None
        row.last_rotated_at = datetime.now(timezone.utc) - timedelta(days=80)
        row.rotation_due_at = datetime.now(timezone.utc) + timedelta(days=5)
        row.status = "HEALTHY"
        session.commit()
        assert compute_status(row) == "ROTATION_DUE"
        row.rotation_due_at = datetime.now(timezone.utc) - timedelta(days=1)
        session.commit()
        assert compute_status(row) == "OVERDUE"
    finally:
        session.close()
    updated = scan_rotation_statuses()
    assert updated >= 1
    listed = client.get("/api/v1/credentials", params={"status": "overdue"}).json()["items"]
    assert any(item["id"] == created["id"] for item in listed)
    scan = client.post("/api/v1/jobs/credentials/rotation-status-scan")
    assert scan.status_code == 200


def test_history_and_filters() -> None:
    aws = _create_aws()
    _create_alibaba()
    history = client.get(f"/api/v1/credentials/{aws['id']}/history", headers=_headers("SecurityAuditor")).json()["items"]
    assert history
    assert all("secretValue" not in item for item in history)
    due = client.get("/api/v1/credentials", params={"status": "rotation_due"}).json()
    assert due["items"] == [] or all(item["status"] == "ROTATION_DUE" for item in due["items"])


def test_update_rejects_secret_value() -> None:
    created = _create_aws()
    response = client.post(
        f"/api/v1/credentials/{created['id']}",
        json={"secretValue": "should-not-work", "rotationPolicyDays": 30},
        headers=_headers(),
    )
    assert response.status_code == 400


def test_principal_permissions_cover_required_roles() -> None:
    admin = Principal("a", "PlatformAdmin", ROLE_PERMISSIONS["PlatformAdmin"])
    assert admin.can("credential:prod_update")
    engineer = Principal("b", "DevOpsEngineer", ROLE_PERMISSIONS["DevOpsEngineer"])
    assert engineer.can("credential:rotate")
    assert not engineer.can("credential:prod_update")
    auditor = Principal("c", "SecurityAuditor", ROLE_PERMISSIONS["SecurityAuditor"])
    assert auditor.can("credential:read_history")
    assert not auditor.can("credential:create")
