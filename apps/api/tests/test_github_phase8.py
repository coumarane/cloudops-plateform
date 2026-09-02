from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from app.core.config import settings
from app.core.rbac import ROLE_PERMISSIONS
from app.db.models import (
    GithubAuditRow,
    GithubEnvironmentMappingRow,
    GithubIntegrationRow,
    GithubRepositoryRow,
    GithubSecretRow,
    GithubWebhookDeliveryRow,
    GithubWorkflowJobRow,
    GithubWorkflowRunRow,
    GithubWorkflowRow,
)
from app.db.session import SessionLocal, engine
from app.integrations.github.auth import build_app_jwt
from app.integrations.github.client import GitHubClient
from app.integrations.github.exceptions import GitHubWebhookError
from app.integrations.github.mapper import normalize_run_status
from app.integrations.scm.base import (
    ScmJob,
    ScmOrganization,
    ScmRepository,
    ScmSecret,
    ScmVariable,
    ScmWorkflow,
    ScmWorkflowRun,
    SourceControlProvider,
)
from app.main import app
from app.secrets.backends.local import LocalDevSecretBackend
from app.services.github_sync import (
    _id,
    ensure_application_link,
    mapped_environment,
    run_repository_sync,
    run_secret_metadata_sync,
    run_variable_sync,
    run_workflow_run_sync,
    run_workflow_sync,
    utcnow,
)
from app.services.github_webhooks import verify_signature

client = TestClient(app)
NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
SECRET_PLAINTEXT = "super-secret-github-value-phase8"


def _headers(role: str = "PlatformAdmin", user: str = "ops@cloudops.local") -> dict[str, str]:
    return {"X-CloudOps-Role": role, "X-CloudOps-User": user}


def _rsa_pem() -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


class FakeProvider(SourceControlProvider):
    name = "github"

    def __init__(self) -> None:
        self.secrets: dict[tuple[str, str, str], str] = {}
        self.orgs = [
            ScmOrganization(external_id="1", login="acme", name="Acme", html_url="https://github.com/acme"),
        ]
        self.repos = [
            ScmRepository(
                external_id="99",
                organization="acme",
                name="payments-api",
                full_name="acme/payments-api",
                default_branch="main",
                html_url="https://github.com/acme/payments-api",
                pushed_at=NOW,
            )
        ]
        self.workflows = [
            ScmWorkflow(
                external_id="10",
                repository_external_id="99",
                name="Deploy",
                path=".github/workflows/deploy.yml",
                state="active",
                html_url="https://github.com/acme/payments-api/actions/workflows/deploy.yml",
            )
        ]
        self.runs = [
            ScmWorkflowRun(
                external_id="500",
                workflow_external_id="10",
                repository_external_id="99",
                branch="main",
                commit_sha="abc1234deadbeef",
                event="push",
                actor="ada",
                status="completed",
                conclusion="failure",
                html_url="https://github.com/acme/payments-api/actions/runs/500",
                started_at=NOW - timedelta(minutes=8),
                completed_at=NOW,
                github_environment="dev",
            )
        ]
        self.jobs = [
            ScmJob(
                external_id="900",
                run_external_id="500",
                name="build",
                status="completed",
                conclusion="failure",
                started_at=NOW - timedelta(minutes=8),
                completed_at=NOW,
                html_url="https://github.com/acme/payments-api/actions/runs/500/job/900",
            )
        ]
        self.variables = [
            ScmVariable(name="LOG_LEVEL", value="info", scope="repository", organization="acme", updated_at=NOW),
            ScmVariable(
                name="DB_HOST",
                value="sensitive-host",
                scope="environment",
                organization="acme",
                github_environment="dev",
                updated_at=NOW,
                sensitive=True,
            ),
        ]
        self.secret_meta = [
            ScmSecret(name="DEPLOY_TOKEN", scope="repository", organization="acme", updated_at=NOW),
        ]

    def list_organizations(self) -> list[ScmOrganization]:
        return list(self.orgs)

    def list_repositories(self) -> list[ScmRepository]:
        return list(self.repos)

    def list_workflows(self, repository: ScmRepository) -> list[ScmWorkflow]:
        return list(self.workflows)

    def list_workflow_runs(self, repository: ScmRepository, *, since: datetime | None = None) -> list[ScmWorkflowRun]:
        return list(self.runs)

    def list_jobs(self, run: ScmWorkflowRun, repository: ScmRepository | None = None) -> list[ScmJob]:
        return list(self.jobs)

    def list_variables(self, repository: ScmRepository) -> list[ScmVariable]:
        return list(self.variables)

    def list_secrets(self, repository: ScmRepository) -> list[ScmSecret]:
        return list(self.secret_meta)

    def put_secret(self, *, repository: ScmRepository, name: str, value: str, github_environment: str = "") -> None:
        self.secrets[(repository.full_name, name, github_environment)] = value

    def delete_secret(self, *, repository: ScmRepository, name: str, github_environment: str = "") -> None:
        self.secrets.pop((repository.full_name, name, github_environment), None)

    def put_variable(
        self,
        *,
        repository: ScmRepository,
        name: str,
        value: str,
        github_environment: str = "",
        sensitive: bool = False,
    ) -> None:
        return None

    def delete_variable(self, *, repository: ScmRepository, name: str, github_environment: str = "") -> None:
        return None


def _seed_repo(session, provider: FakeProvider) -> GithubRepositoryRow:
    run_repository_sync(provider=provider)
    repo = session.scalar(select(GithubRepositoryRow).where(GithubRepositoryRow.full_name == "acme/payments-api"))
    assert repo is not None
    return repo


def test_github_app_jwt_round_trip() -> None:
    pem = _rsa_pem()
    LocalDevSecretBackend().store_secret("local://github-app", pem)
    token = build_app_jwt("12345", pem, now=1_700_000_000)
    parts = token.split(".")
    assert len(parts) == 3
    assert all(parts)


def test_status_normalization() -> None:
    assert normalize_run_status("queued", None) == "QUEUED"
    assert normalize_run_status("in_progress", None) == "RUNNING"
    assert normalize_run_status("completed", "success") == "SUCCEEDED"
    assert normalize_run_status("completed", "failure") == "FAILED"
    assert normalize_run_status("completed", "cancelled") == "CANCELLED"
    assert normalize_run_status("completed", "skipped") == "SKIPPED"
    assert normalize_run_status("", "") == "UNKNOWN"


def test_repository_workflow_and_run_sync() -> None:
    provider = FakeProvider()
    assert run_repository_sync(provider=provider) == 1
    assert run_workflow_sync(provider=provider) == 1
    assert run_workflow_run_sync(provider=provider) == 1
    session = SessionLocal()
    try:
        repo = session.scalar(select(GithubRepositoryRow))
        workflow = session.scalar(select(GithubWorkflowRow))
        run = session.scalar(select(GithubWorkflowRunRow))
        job = session.scalar(select(GithubWorkflowJobRow))
        assert repo is not None and repo.full_name == "acme/payments-api"
        assert workflow is not None and workflow.path.endswith("deploy.yml")
        assert run is not None and run.status == "FAILED" and run.github_status == "completed"
        assert job is not None and job.name == "build"
        assert session.scalar(select(GithubIntegrationRow)) is not None
    finally:
        session.close()
    overview = client.get("/api/v1/scm/overview", headers=_headers()).json()
    assert overview["repositories"] == 1
    assert overview["failedWorkflows"] == 1
    assert "secret" not in json.dumps(overview).lower() or "••••" in json.dumps(overview)


def test_environment_mapping_and_correlation() -> None:
    provider = FakeProvider()
    session = SessionLocal()
    try:
        repo = _seed_repo(session, provider)
        mapping_id = _id("ghem", repo.id, "dev")
        session.add(
            GithubEnvironmentMappingRow(
                id=mapping_id,
                github_repository_id=repo.id,
                github_environment="dev",
                cloudops_environment_id="aws-emea-nonprod-dev",
                active=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        session.commit()
        mapped = mapped_environment(session, repo.id, "dev")
        assert mapped is not None
        assert mapped.environment == "DEV"
        ensure_application_link(session, repo.id, "app-AWS-EMEA-UAT-payment-gateway-svc")
        session.commit()
    finally:
        session.close()
    run_workflow_sync(provider=provider)
    run_workflow_run_sync(provider=provider)
    response = client.get("/api/v1/scm/workflow-runs", headers=_headers())
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["cloudopsEnvironmentId"] == "aws-emea-nonprod-dev"
    assert item["environment"] == "DEV"
    assert item["applicationId"]


def test_secret_replace_never_persists_or_logs_plaintext(caplog, monkeypatch) -> None:
    provider = FakeProvider()
    monkeypatch.setattr("app.services.github_secrets.get_scm_provider", lambda: provider)
    session = SessionLocal()
    try:
        repo = _seed_repo(session, provider)
        repo_id = repo.id
    finally:
        session.close()
    with caplog.at_level("INFO"):
        created = client.post(
            "/api/v1/scm/secrets",
            headers=_headers(),
            json={
                "repositoryId": repo_id,
                "name": "DEPLOY_TOKEN",
                "value": SECRET_PLAINTEXT,
                "scope": "repository",
            },
        )
    assert created.status_code == 200
    body = created.json()
    assert body["value"] == "••••••••••••"
    assert SECRET_PLAINTEXT not in json.dumps(body)
    assert SECRET_PLAINTEXT not in caplog.text
    dumped = " ".join(str(row) for row in engine.connect().execute(text("SELECT * FROM github_secrets")))
    assert SECRET_PLAINTEXT not in dumped
    session = SessionLocal()
    try:
        row = session.scalar(select(GithubSecretRow))
        assert row is not None
        assert not hasattr(row, "value") or getattr(row, "value", None) in {None, ""}
        columns = {column["name"] for column in inspect(engine).get_columns("github_secrets")}
        assert "value" not in columns
        assert "encrypted_value" not in columns
        audit = session.scalar(select(GithubAuditRow).where(GithubAuditRow.action == "GITHUB_SECRET_CREATED"))
        assert audit is not None
        assert SECRET_PLAINTEXT not in audit.detail
    finally:
        session.close()
    listed = client.get("/api/v1/scm/secrets", headers=_headers()).json()
    assert listed["items"][0]["value"] == "••••••••••••"
    assert "Reveal" not in json.dumps(listed)
    assert "View Secret" not in json.dumps(listed)


def test_prd_secret_requires_prod_permission_confirmation_and_reason(monkeypatch) -> None:
    provider = FakeProvider()
    monkeypatch.setattr("app.services.github_secrets.get_scm_provider", lambda: provider)
    session = SessionLocal()
    try:
        repo = _seed_repo(session, provider)
        session.add(
            GithubEnvironmentMappingRow(
                id=_id("ghem", repo.id, "prd"),
                github_repository_id=repo.id,
                github_environment="prd",
                cloudops_environment_id="aws-emea-prod-prd",
                active=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        session.commit()
        repo_id = repo.id
    finally:
        session.close()
    denied = client.post(
        "/api/v1/scm/secrets",
        headers=_headers("DevOpsEngineer"),
        json={
            "repositoryId": repo_id,
            "name": "PROD_TOKEN",
            "value": "prd-secret",
            "githubEnvironment": "prd",
            "confirmed": True,
            "reason": "rotate",
        },
    )
    assert denied.status_code == 403
    missing = client.post(
        "/api/v1/scm/secrets",
        headers=_headers(),
        json={
            "repositoryId": repo_id,
            "name": "PROD_TOKEN",
            "value": "prd-secret",
            "githubEnvironment": "prd",
        },
    )
    assert missing.status_code == 400
    ok = client.post(
        "/api/v1/scm/secrets",
        headers=_headers(),
        json={
            "repositoryId": repo_id,
            "name": "PROD_TOKEN",
            "value": "prd-secret",
            "githubEnvironment": "prd",
            "confirmed": True,
            "reason": "Emergency rotation",
            "changeTicket": "CHG-1",
        },
    )
    assert ok.status_code == 200


def test_rbac_github_permissions() -> None:
    assert "github_secret:prod_update" in ROLE_PERMISSIONS["PlatformAdmin"]
    assert "github_secret:prod_update" not in ROLE_PERMISSIONS["DevOpsEngineer"]
    assert "github:read" in ROLE_PERMISSIONS["Developer"]
    assert "github_secret:create" not in ROLE_PERMISSIONS["Developer"]
    denied = client.get("/api/v1/scm/overview", headers=_headers("ReadOnly"))
    assert denied.status_code == 200
    sync = client.post("/api/v1/scm/sync", headers=_headers("Developer"))
    assert sync.status_code == 403
    auditor = client.get("/api/v1/scm/secrets", headers=_headers("SecurityAuditor"))
    assert auditor.status_code == 200


def test_webhook_signature_and_idempotency(monkeypatch) -> None:
    monkeypatch.setattr(settings, "github_webhook_secret", "webhook-secret")
    body = json.dumps({"action": "completed", "workflow_run": {"id": 1}}).encode()
    try:
        verify_signature(body, None, "webhook-secret")
        raise AssertionError("unsigned webhook must be rejected")
    except GitHubWebhookError:
        pass
    bad = client.post(
        "/api/v1/integrations/github/webhook",
        content=body,
        headers={"X-GitHub-Event": "workflow_run", "X-GitHub-Delivery": str(uuid4())},
    )
    assert bad.status_code == 400
    digest = "sha256=" + hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    delivery = str(uuid4())
    first = client.post(
        "/api/v1/integrations/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "workflow_run",
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": digest,
        },
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/integrations/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "workflow_run",
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": digest,
        },
    )
    assert second.json()["duplicate"] is True
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubWebhookDeliveryRow).where(GithubWebhookDeliveryRow.delivery_id == delivery)))
        assert len(rows) == 1
    finally:
        session.close()


def test_duplicate_workflow_events_do_not_duplicate_runs() -> None:
    provider = FakeProvider()
    run_repository_sync(provider=provider)
    run_workflow_sync(provider=provider)
    run_workflow_run_sync(provider=provider)
    run_workflow_run_sync(provider=provider)
    session = SessionLocal()
    try:
        assert session.query(GithubWorkflowRunRow).count() == 1
        assert session.query(GithubWorkflowJobRow).count() == 1
    finally:
        session.close()


def test_variable_sync_masks_sensitive_values() -> None:
    provider = FakeProvider()
    run_repository_sync(provider=provider)
    run_variable_sync(provider=provider)
    payload = client.get("/api/v1/scm/variables", headers=_headers()).json()
    names = {item["name"]: item for item in payload["items"]}
    assert names["LOG_LEVEL"]["value"] == "info"
    assert names["DB_HOST"]["value"] == "••••••••••••"
    assert names["DB_HOST"]["sensitive"] is True


def test_secret_metadata_sync_has_no_plaintext() -> None:
    provider = FakeProvider()
    run_repository_sync(provider=provider)
    run_secret_metadata_sync(provider=provider)
    payload = client.get("/api/v1/scm/secrets", headers=_headers()).json()
    assert payload["items"][0]["value"] == "••••••••••••"
    assert SECRET_PLAINTEXT not in json.dumps(payload)


def test_rate_limit_backoff() -> None:
    calls = {"n": 0}

    def http(method: str, url: str, headers: dict[str, str], body: bytes | None):
        calls["n"] += 1
        if calls["n"] == 1:
            return 403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(int(NOW.timestamp()) + 2)}, b"rate"
        return 200, {"x-ratelimit-remaining": "10"}, b'{"ok": true}'

    slept: list[float] = []
    client_api = GitHubClient(api_url="https://api.github.com", token="t", http=http, sleep=slept.append, max_retries=2)
    payload = client_api.request("GET", "/rate")
    assert payload == {"ok": True}
    assert slept
    assert client_api.rate_limit_remaining == 10


def test_beat_schedules_come_from_settings() -> None:
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from celery_app import celery_app as worker_app

    schedule = worker_app.conf.beat_schedule
    assert schedule["github-repository-sync"]["schedule"] == settings.github_repository_sync_interval_seconds
    assert schedule["github-workflow-sync"]["schedule"] == settings.github_workflow_sync_interval_seconds
    assert schedule["github-workflow-run-sync"]["schedule"] == settings.github_workflow_run_sync_interval_seconds
    assert schedule["github-variable-sync"]["schedule"] == settings.github_variable_sync_interval_seconds
    assert schedule["github-secret-metadata-sync"]["schedule"] == settings.github_secret_sync_interval_seconds


def test_migration_does_not_store_private_keys() -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("github_integrations")}
    assert "private_key" not in columns
    assert "private_key_pem" not in columns
    assert "private_key_ref" in columns
    secret_columns = {column["name"] for column in inspect(engine).get_columns("github_secrets")}
    assert "value" not in secret_columns


def test_github_secret_sealed_box_encryption() -> None:
    from base64 import b64decode

    from nacl import encoding, public

    from app.integrations.github.crypto import encrypt_secret

    key = public.PrivateKey.generate()
    encrypted = encrypt_secret(key.public_key.encode(encoding.Base64Encoder()).decode(), "hello-github")
    assert "hello-github" not in encrypted
    box = public.SealedBox(key)
    assert box.decrypt(b64decode(encrypted)) == b"hello-github"
