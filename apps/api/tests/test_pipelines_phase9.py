from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.rbac import ROLE_PERMISSIONS
from app.db.models import (
    PipelineAlertRow,
    PipelineJobRow,
    PipelineProviderRow,
    PipelineRow,
    PipelineRunRow,
    PipelineStageRow,
    PipelineWebhookDeliveryRow,
)
from app.db.session import SessionLocal
from app.integrations.pipelines import override_pipeline_providers
from app.integrations.pipelines.azure_devops import MockAzureDevOpsProvider
from app.integrations.pipelines.base import ProviderPipeline, ProviderPipelineJob, ProviderPipelineRun, ProviderPipelineStage
from app.integrations.pipelines.github import GitHubActionsPipelineProvider
from app.integrations.pipelines.status import normalize_azure, normalize_github
from app.main import app
from app.services.github_sync import run_repository_sync, run_workflow_run_sync, run_workflow_sync
from app.services.pipeline_sync import (
    match_environment,
    run_pipeline_run_sync,
    run_pipeline_sync,
)
from app.services.pipeline_webhooks import verify_azure_webhook
from tests.test_github_phase8 import FakeProvider, _headers

client = TestClient(app)
NOW = datetime(2026, 9, 2, 16, 0, tzinfo=timezone.utc)


def _seed_github(monkeypatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr("app.services.github_sync.get_scm_provider", lambda: provider)
    run_repository_sync(provider=provider)
    run_workflow_sync(provider=provider)
    run_workflow_run_sync(provider=provider)
    return provider


def test_pipeline_status_normalization() -> None:
    assert normalize_github("queued", None) == "QUEUED"
    assert normalize_github("waiting", None) == "WAITING"
    assert normalize_github("in_progress", None) == "RUNNING"
    assert normalize_github("completed", "success") == "SUCCEEDED"
    assert normalize_github("completed", "failure") == "FAILED"
    assert normalize_azure("notStarted", None) == "QUEUED"
    assert normalize_azure("inProgress", None) == "RUNNING"
    assert normalize_azure("completed", "succeeded") == "SUCCEEDED"
    assert normalize_azure("completed", "failed") == "FAILED"
    assert normalize_azure("completed", "succeededWithIssues") == "PARTIAL"
    assert normalize_azure("completed", "canceled") == "CANCELLED"


def test_github_workflow_maps_to_pipeline(monkeypatch) -> None:
    _seed_github(monkeypatch)
    run_pipeline_sync()
    session = SessionLocal()
    try:
        pipeline = session.scalar(select(PipelineRow).where(PipelineRow.name == "Deploy"))
        assert pipeline is not None
        assert pipeline.external_id == "10"
        provider = session.scalar(select(PipelineProviderRow).where(PipelineProviderRow.key == "github-actions"))
        assert provider is not None
        assert pipeline.provider_id == provider.id
        runs = list(session.scalars(select(PipelineRunRow).where(PipelineRunRow.pipeline_id == pipeline.id)))
        assert len(runs) == 1
        assert runs[0].external_run_id == "500"
        assert runs[0].status == "FAILED"
        assert runs[0].commit_sha == "abc1234deadbeef"
        assert runs[0].deployment_id
    finally:
        session.close()


def test_environment_mapping_and_correlation(monkeypatch) -> None:
    _seed_github(monkeypatch)
    session = SessionLocal()
    try:
        from app.services.pipeline_sync import _id, ensure_provider_rows, utcnow
        from app.db.models import PipelineEnvironmentMappingRow

        pipeline = session.scalar(select(PipelineRow).where(PipelineRow.name == "Deploy"))
        assert pipeline is not None
        mapping = PipelineEnvironmentMappingRow(
            id=_id("pem", pipeline.id, "aws-emea-nonprod-uat", "main", ""),
            pipeline_id=pipeline.id,
            environment_id="aws-emea-nonprod-uat",
            branch_pattern="main",
            stage_name="",
            active=True,
            priority=10,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(mapping)
        session.commit()
        run = session.scalar(select(PipelineRunRow).where(PipelineRunRow.pipeline_id == pipeline.id))
        matched = match_environment(session, pipeline, run)
        assert matched is not None
        assert matched.id == "aws-emea-nonprod-uat"
        run.environment_id = "aws-emea-nonprod-uat"
        session.commit()
        assert run.environment_id == "aws-emea-nonprod-uat"
        assert run.commit_sha
        assert run.deployment_id
    finally:
        session.close()


def test_provider_isolation(monkeypatch) -> None:
    _seed_github(monkeypatch)
    azure = MockAzureDevOpsProvider(
        pipelines=[ProviderPipeline(external_id="88", name="customer-api")],
        runs=[],
    )
    azure.fail_list = True

    def providers(session=None):
        items = []
        if session is not None:
            items.append(GitHubActionsPipelineProvider(session))
        items.append(azure)
        return items

    monkeypatch.setattr("app.services.pipeline_sync.get_pipeline_providers", providers)
    count = run_pipeline_sync()
    assert count >= 1
    session = SessionLocal()
    try:
        provider = session.scalar(select(PipelineProviderRow).where(PipelineProviderRow.key == "azure-devops"))
        assert provider is not None
        assert provider.status == "error"
        github_provider = session.scalar(select(PipelineProviderRow).where(PipelineProviderRow.key == "github-actions"))
        assert github_provider is not None
        assert github_provider.status == "ok"
        assert session.scalar(select(PipelineRow).where(PipelineRow.name == "Deploy")) is not None
    finally:
        session.close()


def test_api_filtering_and_rbac(monkeypatch) -> None:
    _seed_github(monkeypatch)
    listed = client.get("/api/v1/pipelines", headers=_headers())
    assert listed.status_code == 200
    names = {item["name"] for item in listed.json()["items"]}
    assert "Deploy" in names
    failed = client.get("/api/v1/pipeline-runs", params={"status": "FAILED"}, headers=_headers())
    assert failed.status_code == 200
    assert failed.json()["items"]
    github_only = client.get("/api/v1/pipelines", params={"provider": "github-actions"}, headers=_headers())
    assert all(item["providerKey"] == "github-actions" for item in github_only.json()["items"])
    denied = client.get("/api/v1/pipelines", headers=_headers("Developer"))
    assert denied.status_code == 200
    forbidden = client.post("/api/v1/pipelines/sync", headers=_headers("Developer"))
    assert forbidden.status_code == 403
    auditor = client.get("/api/v1/pipelines", headers=_headers("SecurityAuditor"))
    assert auditor.status_code == 200
    mapping_denied = client.post(
        "/api/v1/pipelines/missing/environment-mappings",
        json={"environmentId": "aws-emea-nonprod-uat", "branchPattern": "main"},
        headers=_headers("Developer"),
    )
    assert mapping_denied.status_code == 403
    assert "pipeline:read" in ROLE_PERMISSIONS["Developer"]
    assert "pipeline:sync" in ROLE_PERMISSIONS["DevOpsEngineer"]
    assert "pipeline:run" not in ROLE_PERMISSIONS["DevOpsEngineer"]
    assert "pipeline:run" in ROLE_PERMISSIONS["PlatformAdmin"]


def test_alert_deduplication(monkeypatch) -> None:
    _seed_github(monkeypatch)
    session = SessionLocal()
    try:
        from app.db.models import PipelineEnvironmentMappingRow
        from app.services.pipeline_sync import _id, correlate_run, evaluate_run_alert, utcnow

        pipeline = session.scalar(select(PipelineRow).where(PipelineRow.name == "Deploy"))
        run = session.scalar(select(PipelineRunRow).where(PipelineRunRow.pipeline_id == pipeline.id))
        run.environment_id = "aws-emea-nonprod-uat"
        session.add(
            PipelineEnvironmentMappingRow(
                id=_id("pem", pipeline.id, "aws-emea-nonprod-uat", "*", ""),
                pipeline_id=pipeline.id,
                environment_id="aws-emea-nonprod-uat",
                branch_pattern="*",
                active=True,
                priority=1,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        correlate_run(session, pipeline, run)
        evaluate_run_alert(session, pipeline, run)
        session.flush()
        evaluate_run_alert(session, pipeline, run)
        session.commit()
        alerts = list(session.scalars(select(PipelineAlertRow).where(PipelineAlertRow.run_id == run.id)))
        assert len(alerts) == 1
        assert alerts[0].kind == "PIPELINE_FAILED"
        run.status = "SUCCEEDED"
        evaluate_run_alert(session, pipeline, run)
        session.commit()
        session.refresh(alerts[0])
        assert alerts[0].status == "RESOLVED"
    finally:
        session.close()


def test_webhook_signature_and_idempotency() -> None:
    from app.core.config import settings

    secret = "ado-hook-secret"
    settings.azure_devops_webhook_secret = secret
    body = json.dumps(
        {
            "eventType": "build.complete",
            "notificationId": "n-1",
            "resource": {
                "id": 77,
                "status": "completed",
                "result": "failed",
                "sourceBranch": "refs/heads/main",
                "sourceVersion": "abc1234",
                "pipeline": {"id": 12, "name": "payments-deploy"},
            },
        }
    ).encode()
    token = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={token}"}
    verify_azure_webhook(headers, body)
    first = client.post("/api/v1/integrations/azure-devops/webhook", content=body, headers=headers)
    assert first.status_code == 200
    assert first.json()["queued"] is True
    second = client.post("/api/v1/integrations/azure-devops/webhook", content=body, headers=headers)
    assert second.json()["duplicate"] is True
    unsigned = client.post("/api/v1/integrations/azure-devops/webhook", content=body, headers={})
    assert unsigned.status_code == 401
    settings.azure_devops_webhook_secret = ""
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(PipelineWebhookDeliveryRow)))
        assert len(rows) == 1
        runs = list(session.scalars(select(PipelineRunRow).where(PipelineRunRow.external_run_id == "77")))
        assert len(runs) <= 1
    finally:
        session.close()


def test_basic_auth_webhook_and_no_duplicate_runs() -> None:
    from app.core.config import settings

    secret = "ado-basic"
    settings.azure_devops_webhook_secret = secret
    body = json.dumps(
        {
            "eventType": "ms.vss-pipelines.run-state-changed-event",
            "id": "delivery-2",
            "resource": {
                "id": 77,
                "state": "completed",
                "result": "failed",
                "pipeline": {"id": 12, "name": "payments-deploy"},
            },
        }
    ).encode()
    basic = base64.b64encode(f":{secret}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}"}
    first = client.post("/api/v1/integrations/azure-devops/webhook", content=body, headers=headers)
    second = client.post("/api/v1/integrations/azure-devops/webhook", content=body, headers=headers)
    assert first.status_code == 200
    assert second.json()["duplicate"] is True
    settings.azure_devops_webhook_secret = ""
    session = SessionLocal()
    try:
        runs = list(session.scalars(select(PipelineRunRow).where(PipelineRunRow.external_run_id == "77")))
        assert len(runs) == 1
    finally:
        session.close()


def test_celery_retry_configuration() -> None:
    import sys
    from pathlib import Path

    from app.core.config import settings

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from celery_app import celery_app as worker_app
    from tasks.pipeline_sync import sync_pipelines
    from tasks.pipeline_run_sync import sync_runs

    assert sync_pipelines.max_retries == 3
    assert sync_runs.max_retries == 3
    schedule = worker_app.conf.beat_schedule
    assert schedule["pipeline-sync"]["schedule"] == settings.pipeline_metadata_sync_interval_seconds
    assert schedule["pipeline-run-sync"]["schedule"] == settings.pipeline_run_sync_interval_seconds
    assert schedule["pipeline-run-detail-sync"]["schedule"] == settings.pipeline_running_sync_interval_seconds


def test_azure_adapter_normalizes_runs() -> None:
    azure = MockAzureDevOpsProvider(
        pipelines=[ProviderPipeline(external_id="1", name="web-frontend")],
        runs=[
            ProviderPipelineRun(
                external_id="9",
                pipeline_external_id="1",
                branch="develop",
                commit_sha="fff111",
                trigger="manual",
                actor="ops",
                status="completed",
                result="succeeded",
                started_at=NOW - timedelta(minutes=3),
                completed_at=NOW,
            )
        ],
    )
    azure._stages["9"] = [
        ProviderPipelineStage(external_id="s1", run_external_id="9", name="Build", status="completed", result="succeeded", sort_order=1)
    ]
    azure._jobs["9"] = [
        ProviderPipelineJob(external_id="j1", run_external_id="9", name="compile", status="completed", result="succeeded", stage_external_id="s1")
    ]
    override_pipeline_providers([azure])
    try:
        run_pipeline_sync()
        run_pipeline_run_sync()
        session = SessionLocal()
        try:
            pipeline = session.scalar(select(PipelineRow).where(PipelineRow.name == "web-frontend"))
            assert pipeline is not None
            run = session.scalar(select(PipelineRunRow).where(PipelineRunRow.pipeline_id == pipeline.id))
            assert run is not None
            assert run.status == "SUCCEEDED"
            assert run.branch == "develop"
            stages = list(session.scalars(select(PipelineStageRow).where(PipelineStageRow.run_id == run.id)))
            jobs = list(session.scalars(select(PipelineJobRow).where(PipelineJobRow.run_id == run.id)))
            assert [item.name for item in stages] == ["Build"]
            assert [item.name for item in jobs] == ["compile"]
            detail = client.get(f"/api/v1/pipeline-runs/{run.id}", headers=_headers()).json()
            assert detail["stages"][0]["name"] == "Build"
            assert detail["jobs"][0]["name"] == "compile"
        finally:
            session.close()
    finally:
        override_pipeline_providers(None)


def test_mapping_api_recorrelates_existing_runs(monkeypatch) -> None:
    _seed_github(monkeypatch)
    run_pipeline_sync()
    session = SessionLocal()
    try:
        pipeline = session.scalar(select(PipelineRow).where(PipelineRow.name == "Deploy"))
        run = session.scalar(select(PipelineRunRow).where(PipelineRunRow.pipeline_id == pipeline.id))
        assert pipeline is not None
        assert run is not None
        pipeline_id = pipeline.id
        run_id = run.id
    finally:
        session.close()
    created = client.post(
        f"/api/v1/pipelines/{pipeline_id}/environment-mappings",
        json={"environmentId": "aws-emea-nonprod-uat", "branchPattern": "main", "priority": 20},
        headers=_headers(),
    )
    assert created.status_code == 200
    linked = client.post(
        f"/api/v1/pipelines/{pipeline_id}/application-mappings",
        json={"applicationId": "app-AWS-EMEA-UAT-payment-gateway-svc"},
        headers=_headers(),
    )
    assert linked.status_code == 200
    session = SessionLocal()
    try:
        run = session.get(PipelineRunRow, run_id)
        assert run is not None
        assert run.environment_id == "aws-emea-nonprod-uat"
        assert run.application_id == "app-AWS-EMEA-UAT-payment-gateway-svc"
    finally:
        session.close()
    body = client.get("/api/v1/environments/aws/emea/uat").json()
    app = next(item for item in body["applications"] if item["id"] == "app-AWS-EMEA-UAT-payment-gateway-svc")
    assert app["pipelineId"] == pipeline_id
    assert app["pipelineName"] == "Deploy"
    assert app["latestPipelineRunId"]
    assert any("Deploy" in (item.get("title") or "") for item in body["pipelines"])

