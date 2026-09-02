from __future__ import annotations

import hashlib
import hmac
import json
from uuid import uuid4

from sqlalchemy import select

from app.core.config import settings
from app.core.metrics import inc
from app.db.models import GithubRepositoryRow, GithubWebhookDeliveryRow, GithubWorkflowRunRow, GithubWorkflowRow
from app.db.session import SessionLocal
from app.integrations.github.exceptions import GitHubWebhookError
from app.integrations.github.mapper import parse_datetime
from app.integrations.scm.base import ScmJob, ScmWorkflow, ScmWorkflowRun
from app.secrets.factory import secret_backend
from app.services.github_sync import utcnow, upsert_job, upsert_run, upsert_workflow


def verify_signature(payload: bytes, signature_header: str | None, secret: str) -> None:
    if not secret:
        raise GitHubWebhookError("GitHub webhook secret is not configured")
    if not signature_header or not signature_header.startswith("sha256="):
        raise GitHubWebhookError("Missing GitHub webhook signature")
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise GitHubWebhookError("Invalid GitHub webhook signature")


def _webhook_secret() -> str:
    if settings.github_webhook_secret:
        return settings.github_webhook_secret
    if settings.github_webhook_secret_ref:
        return secret_backend().get_secret(settings.github_webhook_secret_ref)
    raise GitHubWebhookError("GitHub webhook secret is not configured")


def accept_webhook(request_headers: dict[str, str], body: bytes) -> dict:
    delivery_id = request_headers.get("x-github-delivery") or request_headers.get("X-GitHub-Delivery") or ""
    event = request_headers.get("x-github-event") or request_headers.get("X-GitHub-Event") or ""
    signature = request_headers.get("x-hub-signature-256") or request_headers.get("X-Hub-Signature-256")
    verify_signature(body, signature, _webhook_secret())
    if not delivery_id:
        raise GitHubWebhookError("Missing X-GitHub-Delivery")
    digest = hashlib.sha256(body).hexdigest()
    session = SessionLocal()
    try:
        existing = session.scalar(select(GithubWebhookDeliveryRow).where(GithubWebhookDeliveryRow.delivery_id == delivery_id))
        if existing is not None:
            inc("cloudops_github_webhook_events_total", {"status": "duplicate", "environment_class": "n/a"})
            return {"id": existing.id, "duplicate": True, "queued": False}
        action = ""
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
            action = str(payload.get("action") or "")
        except json.JSONDecodeError as error:
            raise GitHubWebhookError("Invalid webhook JSON") from error
        row = GithubWebhookDeliveryRow(
            id=str(uuid4()),
            delivery_id=delivery_id,
            event=event,
            action=action,
            payload_digest=digest,
            payload_json=body.decode("utf-8")[:200000],
            status="queued",
            created_at=utcnow(),
        )
        session.add(row)
        session.commit()
        inc("cloudops_github_webhook_events_total", {"status": "accepted", "environment_class": "n/a"})
        return {"id": row.id, "duplicate": False, "queued": True, "deliveryId": delivery_id, "event": event}
    finally:
        session.close()


def process_delivery(delivery_id: str) -> None:
    session = SessionLocal()
    try:
        row = session.get(GithubWebhookDeliveryRow, delivery_id) or session.scalar(
            select(GithubWebhookDeliveryRow).where(GithubWebhookDeliveryRow.delivery_id == delivery_id)
        )
        if row is None:
            return
        if row.status == "processed":
            return
        payload = json.loads(row.payload_json or "{}")
        if row.event == "workflow_run":
            _apply_workflow_run(session, payload.get("workflow_run") or payload)
        elif row.event == "workflow_job":
            _apply_workflow_job(session, payload.get("workflow_job") or payload)
        elif row.event == "push":
            _apply_push(session, payload)
        elif row.event in {"deployment", "deployment_status"}:
            _apply_deployment(session, payload)
        row.status = "processed"
        row.processed_at = utcnow()
        session.commit()
    except Exception:
        session.rollback()
        inc("cloudops_github_webhook_failures_total", {"status": "failed"})
        raise
    finally:
        session.close()


def process_webhook_payload(event: str, payload: dict) -> None:
    session = SessionLocal()
    try:
        if event == "workflow_run":
            _apply_workflow_run(session, payload.get("workflow_run") or payload)
        elif event == "workflow_job":
            _apply_workflow_job(session, payload.get("workflow_job") or payload)
        elif event == "push":
            _apply_push(session, payload)
        elif event in {"deployment", "deployment_status"}:
            _apply_deployment(session, payload)
        session.commit()
    finally:
        session.close()


def _repo_row(session, payload: dict) -> GithubRepositoryRow | None:
    repo_payload = payload.get("repository") if "full_name" not in payload else payload
    if not isinstance(repo_payload, dict):
        return None
    github_id = str(repo_payload.get("id") or "")
    full_name = str(repo_payload.get("full_name") or "")
    if github_id:
        row = session.scalar(select(GithubRepositoryRow).where(GithubRepositoryRow.github_id == github_id))
        if row is not None:
            return row
    if full_name:
        return session.scalar(select(GithubRepositoryRow).where(GithubRepositoryRow.full_name == full_name))
    return None


def _apply_workflow_run(session, payload: dict) -> None:
    repo = _repo_row(session, payload)
    if repo is None:
        return
    workflow_id = str((payload.get("workflow_id") or payload.get("workflow", {}).get("id") or ""))
    workflow = session.scalar(select(GithubWorkflowRow).where(GithubWorkflowRow.github_id == workflow_id))
    if workflow is None:
        workflow = upsert_workflow(
            session,
            repo,
            ScmWorkflow(
                external_id=workflow_id or str(payload.get("id")),
                repository_external_id=repo.github_id,
                name=str((payload.get("name") or "workflow")),
                path=str(payload.get("path") or ""),
                state="active",
                html_url=str(payload.get("html_url") or ""),
            ),
        )
    actor = payload.get("actor") or {}
    upsert_run(
        session,
        repo,
        workflow,
        ScmWorkflowRun(
            external_id=str(payload.get("id")),
            workflow_external_id=workflow.github_id,
            repository_external_id=repo.github_id,
            branch=str(payload.get("head_branch") or ""),
            commit_sha=str(payload.get("head_sha") or ""),
            event=str(payload.get("event") or ""),
            actor=str(actor.get("login") or ""),
            status=str(payload.get("status") or ""),
            conclusion=str(payload.get("conclusion") or ""),
            html_url=str(payload.get("html_url") or ""),
            started_at=parse_datetime(payload.get("run_started_at") or payload.get("created_at")),
            completed_at=parse_datetime(payload.get("updated_at") if payload.get("status") == "completed" else None),
            run_attempt=int(payload.get("run_attempt") or 1),
            github_environment=_environment_name(payload),
        ),
    )


def _environment_name(payload: dict) -> str:
    value = payload.get("environment") or payload.get("github_environment")
    if isinstance(value, dict):
        return str(value.get("name") or "")
    return str(value or "")


def _apply_workflow_job(session, payload: dict) -> None:
    run_github_id = str(payload.get("run_id") or "")
    run = session.scalar(select(GithubWorkflowRunRow).where(GithubWorkflowRunRow.github_id == run_github_id))
    if run is None:
        return
    upsert_job(
        session,
        run,
        ScmJob(
            external_id=str(payload.get("id")),
            run_external_id=run_github_id,
            name=str(payload.get("name") or "job"),
            status=str(payload.get("status") or ""),
            conclusion=str(payload.get("conclusion") or ""),
            started_at=parse_datetime(payload.get("started_at")),
            completed_at=parse_datetime(payload.get("completed_at")),
            runner_name=str(payload.get("runner_name") or ""),
            runner_group=str(payload.get("runner_group_name") or ""),
            html_url=str(payload.get("html_url") or ""),
        ),
    )


def _apply_push(session, payload: dict) -> None:
    repo = _repo_row(session, payload.get("repository") or payload)
    if repo is None:
        return
    repo.pushed_at = parse_datetime(payload.get("pushed_at") or (payload.get("repository") or {}).get("pushed_at")) or utcnow()


def _apply_deployment(session, payload: dict) -> None:
    repo = _repo_row(session, payload.get("repository") or payload)
    deployment = payload.get("deployment") or payload
    sha = str(deployment.get("sha") or payload.get("sha") or "")
    environment = _environment_name(deployment) or _environment_name(payload)
    if repo is None or not sha:
        return
    runs = list(
        session.scalars(
            select(GithubWorkflowRunRow).where(
                GithubWorkflowRunRow.repository_id == repo.id,
                GithubWorkflowRunRow.commit_sha == sha,
            )
        )
    )
    for run in runs:
        if environment:
            run.github_environment = environment
        from app.services.github_sync import correlate_run

        correlate_run(session, repo, run)
