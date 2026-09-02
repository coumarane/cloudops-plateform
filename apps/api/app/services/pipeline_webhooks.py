from __future__ import annotations

import hashlib
import hmac
import json
from uuid import uuid4

from sqlalchemy import select

from app.core.config import settings
from app.core.metrics import inc
from app.db.models import PipelineProviderRow, PipelineRow, PipelineWebhookDeliveryRow
from app.db.session import SessionLocal
from app.integrations.github.mapper import parse_datetime
from app.integrations.pipelines.base import ProviderPipeline, ProviderPipelineRun
from app.integrations.pipelines.exceptions import PipelineWebhookError
from app.secrets.factory import secret_backend
from app.services.pipeline_sync import ensure_provider_rows, upsert_pipeline, upsert_run, utcnow


def _webhook_secret() -> str:
    if settings.azure_devops_webhook_secret:
        return settings.azure_devops_webhook_secret
    if settings.azure_devops_webhook_secret_ref:
        return secret_backend().get_secret(settings.azure_devops_webhook_secret_ref)
    raise PipelineWebhookError("Azure DevOps webhook secret is not configured")


def verify_azure_webhook(headers: dict[str, str], body: bytes) -> None:
    secret = _webhook_secret()
    token = (
        headers.get("x-azure-devops-token")
        or headers.get("X-Azure-DevOps-Token")
        or ""
    )
    authorization = headers.get("authorization") or headers.get("Authorization") or ""
    signature = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256") or ""
    if token and hmac.compare_digest(token, secret):
        return
    if authorization.lower().startswith("basic "):
        import base64

        try:
            decoded = base64.b64decode(authorization.split(" ", 1)[1]).decode()
        except Exception as error:
            raise PipelineWebhookError("Invalid Azure DevOps webhook signature") from error
        password = decoded.split(":", 1)[-1]
        if hmac.compare_digest(password, secret):
            return
    if signature.startswith("sha256="):
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, signature):
            return
    if not token and not authorization and not signature:
        raise PipelineWebhookError("Missing Azure DevOps webhook signature")
    raise PipelineWebhookError("Invalid Azure DevOps webhook signature")


def accept_azure_webhook(headers: dict[str, str], body: bytes) -> dict:
    verify_azure_webhook(headers, body)
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as error:
        raise PipelineWebhookError("Invalid webhook JSON") from error
    delivery_id = (
        headers.get("x-vss-subscriptionid")
        or headers.get("X-VSS-SubscriptionId")
        or str(payload.get("notificationId") or payload.get("id") or hashlib.sha256(body).hexdigest())
    )
    event = str(payload.get("eventType") or headers.get("x-azure-event") or "azure.devops")
    digest = hashlib.sha256(body).hexdigest()
    session = SessionLocal()
    try:
        existing = session.scalar(
            select(PipelineWebhookDeliveryRow).where(PipelineWebhookDeliveryRow.delivery_id == delivery_id)
        )
        if existing is not None:
            return {"id": existing.id, "duplicate": True, "queued": False}
        row = PipelineWebhookDeliveryRow(
            id=str(uuid4()),
            delivery_id=delivery_id,
            provider_key="azure-devops",
            event=event,
            payload_digest=digest,
            payload_json=body.decode("utf-8")[:200000],
            status="queued",
            created_at=utcnow(),
        )
        session.add(row)
        session.commit()
        return {"id": row.id, "duplicate": False, "queued": True, "deliveryId": delivery_id, "event": event}
    finally:
        session.close()


def process_pipeline_delivery(delivery_id: str) -> None:
    session = SessionLocal()
    try:
        row = session.get(PipelineWebhookDeliveryRow, delivery_id) or session.scalar(
            select(PipelineWebhookDeliveryRow).where(PipelineWebhookDeliveryRow.delivery_id == delivery_id)
        )
        if row is None or row.status == "processed":
            return
        payload = json.loads(row.payload_json or "{}")
        if row.provider_key == "azure-devops":
            _apply_azure_payload(session, payload)
        row.status = "processed"
        row.processed_at = utcnow()
        session.commit()
    except Exception:
        session.rollback()
        inc("cloudops_pipeline_sync_failures_total", {"provider": "azure-devops", "status": "webhook", "environment_class": "n/a"})
        raise
    finally:
        session.close()


def _apply_azure_payload(session, payload: dict) -> None:
    resource = payload.get("resource") or payload
    pipeline_payload = resource.get("pipeline") or resource.get("definition") or {}
    run_id = str(resource.get("id") or resource.get("runId") or "")
    pipeline_id = str(pipeline_payload.get("id") or resource.get("definition", {}).get("id") or "")
    if not run_id or not pipeline_id:
        return
    providers = ensure_provider_rows(session)
    provider_row = providers["azure-devops"]
    pipeline_item = ProviderPipeline(
        external_id=pipeline_id,
        name=str(pipeline_payload.get("name") or resource.get("definition", {}).get("name") or "pipeline"),
        html_url=str((resource.get("_links") or {}).get("web", {}).get("href") or ""),
    )
    pipeline = upsert_pipeline(session, provider_row, pipeline_item)
    run_item = ProviderPipelineRun(
        external_id=run_id,
        pipeline_external_id=pipeline_id,
        branch=str(resource.get("sourceBranch") or "").removeprefix("refs/heads/"),
        commit_sha=str(resource.get("sourceVersion") or ""),
        trigger=str(resource.get("reason") or payload.get("eventType") or ""),
        actor=str((resource.get("requestedBy") or {}).get("displayName") or ""),
        status=str(resource.get("status") or resource.get("state") or ""),
        result=str(resource.get("result") or ""),
        html_url=str((resource.get("_links") or {}).get("web", {}).get("href") or ""),
        started_at=parse_datetime(resource.get("startTime") or resource.get("createdDate")),
        completed_at=parse_datetime(resource.get("finishTime") or resource.get("finishedDate")),
    )
    upsert_run(session, provider_row, pipeline, run_item)
    _ = PipelineRow, PipelineProviderRow
