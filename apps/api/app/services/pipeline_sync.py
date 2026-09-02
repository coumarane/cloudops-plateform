from __future__ import annotations

import fnmatch
import json
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.correlation import current_correlation_id
from app.core.logging import get_logger, sanitize_text
from app.core.metrics import inc, observe_duration, set_gauge
from app.db.models import (
    CloudEnvironmentRow,
    GithubRepositoryRow,
    PipelineAlertRow,
    PipelineApplicationMappingRow,
    PipelineAuditRow,
    PipelineEnvironmentMappingRow,
    PipelineJobRow,
    PipelineProviderRow,
    PipelineRow,
    PipelineRunRow,
    PipelineStageRow,
)
from app.db.repository import InventoryRepository, utcnow
from app.db.session import SessionLocal
from app.integrations.github.mapper import duration_seconds
from app.integrations.pipelines import azure_devops_configured, get_pipeline_providers
from app.integrations.pipelines.base import PipelineProvider, ProviderPipeline, ProviderPipelineRun
from app.integrations.pipelines.status import (
    FAILED,
    RUNNING,
    SUCCEEDED,
    normalize_azure,
    normalize_github,
)

logger = get_logger(__name__)

PROVIDER_SPECS = (
    ("github-actions", "GitHub Actions"),
    ("azure-devops", "Azure DevOps"),
    ("gitlab", "GitLab"),
    ("jenkins", "Jenkins"),
)


def _id(prefix: str, *parts: str) -> str:
    digest = sha256("|".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _meta(data: dict | None) -> str:
    return json.dumps(data or {}, default=str)[:8000]


def _environment_class(environment_id: str | None) -> str:
    environment_id = environment_id or ""
    env = environment_id.lower()
    if env.endswith("-prd") or env.endswith("/prd") or env.endswith("prd"):
        return "PRD"
    if "-npd" in env or env.endswith("npd"):
        return "NPD"
    if "-uat" in env or env.endswith("uat"):
        return "UAT"
    if "int" in env or "tst" in env:
        return "INT/TST"
    if env.endswith("-dev") or env.endswith("dev"):
        return "DEV"
    return ""


def record_audit(
    session: Session,
    action: str,
    *,
    actor: str,
    object_name: str = "",
    pipeline_id: str = "",
    environment: str = "",
    result: str = "succeeded",
    detail: str = "",
) -> None:
    session.add(
        PipelineAuditRow(
            id=str(uuid4()),
            action=action,
            actor=actor,
            object_name=object_name,
            pipeline_id=pipeline_id,
            environment=environment,
            result=result,
            detail=sanitize_text(detail)[:1000],
            correlation_id=current_correlation_id(),
            created_at=utcnow(),
        )
    )


def ensure_provider_rows(session: Session) -> dict[str, PipelineProviderRow]:
    now = utcnow()
    rows: dict[str, PipelineProviderRow] = {}
    for key, name in PROVIDER_SPECS:
        row_id = _id("pp", key)
        row = session.scalar(select(PipelineProviderRow).where(PipelineProviderRow.key == key)) or session.get(
            PipelineProviderRow, row_id
        )
        if row is None:
            row = PipelineProviderRow(id=row_id, key=key, name=name, created_at=now, updated_at=now)
            session.add(row)
        row.name = name
        if key == "github-actions":
            row.organization = settings.github_organization
            row.base_url = settings.github_api_url
            row.auth_ref = settings.github_private_key_ref
            row.enabled = True
            if row.status == "pending":
                row.status = "configured" if settings.github_app_id else "idle"
        elif key == "azure-devops":
            row.organization = settings.azure_devops_organization
            row.project = settings.azure_devops_project
            row.base_url = settings.azure_devops_base_url
            row.auth_ref = settings.azure_devops_auth_ref
            row.enabled = azure_devops_configured() or settings.azure_devops_mock
            if not row.enabled:
                row.status = "disabled"
            elif row.status in {"pending", "disabled"}:
                row.status = "configured"
        else:
            row.enabled = False
            row.status = "stub"
        row.updated_at = now
        rows[key] = row
    session.flush()
    return rows


def normalize_run(provider_key: str, native_status: str, native_result: str) -> str:
    if provider_key == "github-actions":
        return normalize_github(native_status, native_result)
    return normalize_azure(native_status, native_result)


def match_environment(session: Session, pipeline: PipelineRow, run: PipelineRunRow) -> CloudEnvironmentRow | None:
    mappings = list(
        session.scalars(
            select(PipelineEnvironmentMappingRow)
            .where(
                PipelineEnvironmentMappingRow.pipeline_id == pipeline.id,
                PipelineEnvironmentMappingRow.active.is_(True),
            )
            .order_by(PipelineEnvironmentMappingRow.priority.desc())
        )
    )
    branch = run.branch or ""
    for mapping in mappings:
        pattern = mapping.branch_pattern or "*"
        if fnmatch.fnmatch(branch, pattern) or (not branch and pattern in {"*", ""}):
            return session.get(CloudEnvironmentRow, mapping.environment_id)
    return None


def correlate_run(session: Session, pipeline: PipelineRow, run: PipelineRunRow, source: ProviderPipelineRun | None = None) -> None:
    meta = {}
    if source and source.metadata:
        meta = source.metadata
    if meta.get("cloudopsEnvironmentId"):
        run.environment_id = str(meta["cloudopsEnvironmentId"])
    if meta.get("applicationId"):
        run.application_id = str(meta["applicationId"])
    if meta.get("deploymentId"):
        run.deployment_id = str(meta["deploymentId"])
    if meta.get("clusterId"):
        run.cluster_id = str(meta["clusterId"])
    if meta.get("repositoryId"):
        run.repository_id = str(meta["repositoryId"])
    if pipeline.repository_id and not run.repository_id:
        run.repository_id = pipeline.repository_id
    mapped = match_environment(session, pipeline, run)
    if mapped is not None:
        run.environment_id = mapped.id
    app_link = session.scalar(
        select(PipelineApplicationMappingRow).where(PipelineApplicationMappingRow.pipeline_id == pipeline.id)
    )
    if app_link is not None:
        run.application_id = app_link.application_id
        pipeline.application_id = app_link.application_id
    elif pipeline.application_id and not run.application_id:
        run.application_id = pipeline.application_id
    if run.commit_sha:
        run.deployment_id = run.deployment_id or _id("pd", run.repository_id or pipeline.id, run.commit_sha, run.external_run_id)


def evaluate_run_alert(session: Session, pipeline: PipelineRow, run: PipelineRunRow) -> None:
    env_row = session.get(CloudEnvironmentRow, run.environment_id) if run.environment_id else None
    environment = env_row.environment if env_row else _environment_class(run.environment_id)
    configured = {
        "DEV": settings.pipeline_alert_dev,
        "INT/TST": settings.pipeline_alert_int_tst,
        "UAT": settings.pipeline_alert_uat,
        "NPD": settings.pipeline_alert_npd,
        "PRD": settings.pipeline_alert_prd,
    }
    severity = (configured.get(environment) if environment else "") or ""
    alert_id = _id("pla", run.id)
    existing_run = session.get(PipelineAlertRow, alert_id)
    if existing_run is None:
        existing_run = session.scalar(
            select(PipelineAlertRow).where(PipelineAlertRow.run_id == run.id, PipelineAlertRow.status == "OPEN")
        )
    if run.status == SUCCEEDED:
        if existing_run is not None:
            existing_run.status = "RESOLVED"
            existing_run.resolved_at = utcnow()
            existing_run.last_evaluated_at = utcnow()
        for alert in session.scalars(
            select(PipelineAlertRow).where(
                PipelineAlertRow.pipeline_id == pipeline.id,
                PipelineAlertRow.status == "OPEN",
                PipelineAlertRow.environment == environment,
            )
        ):
            if alert.run_id == run.id:
                continue
            alert.status = "RESOLVED"
            alert.resolved_at = utcnow()
            alert.last_evaluated_at = utcnow()
        return
    if run.status != FAILED or not severity:
        return
    if existing_run is not None:
        existing_run.last_evaluated_at = utcnow()
        existing_run.severity = severity
        return
    session.add(
        PipelineAlertRow(
            id=alert_id,
            kind="PIPELINE_FAILED",
            run_id=run.id,
            pipeline_id=pipeline.id,
            environment=environment,
            severity=severity,
            status="OPEN",
            title=f"{pipeline.name} failed",
            created_at=utcnow(),
            last_evaluated_at=utcnow(),
        )
    )
    session.flush()


def upsert_pipeline(session: Session, provider_row: PipelineProviderRow, item: ProviderPipeline) -> PipelineRow:
    row_id = _id("pl", provider_row.key, item.external_id)
    row = session.get(PipelineRow, row_id)
    if row is None:
        existing = session.scalar(
            select(PipelineRow).where(
                PipelineRow.provider_id == provider_row.id,
                PipelineRow.external_id == item.external_id,
            )
        )
        row = existing
    if row is None:
        row = PipelineRow(id=row_id, provider_id=provider_row.id, external_id=item.external_id, name=item.name)
        session.add(row)
    row.name = item.name
    repo_id = item.metadata.get("repositoryId") or ""
    if item.repository_external_id and not repo_id:
        github_repo = session.scalar(
            select(GithubRepositoryRow).where(GithubRepositoryRow.github_id == item.repository_external_id)
        )
        repo_id = github_repo.id if github_repo else item.repository_external_id
    row.repository_id = str(repo_id or row.repository_id or "")
    row.default_branch = item.default_branch or row.default_branch
    row.enabled = item.enabled
    row.html_url = item.html_url
    row.metadata_json = _meta(item.metadata)
    row.last_synced_at = utcnow()
    return row


def upsert_run(
    session: Session,
    provider_row: PipelineProviderRow,
    pipeline: PipelineRow,
    item: ProviderPipelineRun,
) -> PipelineRunRow:
    row_id = _id("prun", pipeline.id, item.external_id)
    row = session.get(PipelineRunRow, row_id)
    if row is None:
        existing = session.scalar(
            select(PipelineRunRow).where(
                PipelineRunRow.pipeline_id == pipeline.id,
                PipelineRunRow.external_run_id == item.external_id,
            )
        )
        row = existing
    now = utcnow()
    if row is None:
        row = PipelineRunRow(
            id=row_id,
            pipeline_id=pipeline.id,
            external_run_id=item.external_id,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
    row.branch = item.branch
    row.commit_sha = item.commit_sha
    row.version = item.version
    row.trigger = item.trigger
    row.actor = item.actor
    row.provider_status = f"{item.status}:{item.result}".strip(":")
    row.status = normalize_run(provider_row.key, item.status, item.result)
    if item.metadata.get("normalizedStatus") and provider_row.key == "github-actions":
        github_native = normalize_github(item.status, item.result)
        row.status = github_native
    row.started_at = item.started_at
    row.completed_at = item.completed_at
    row.duration_seconds = duration_seconds(item.started_at, item.completed_at)
    row.external_url = item.html_url
    row.metadata_json = _meta(item.metadata)
    row.updated_at = now
    correlate_run(session, pipeline, row, item)
    evaluate_run_alert(session, pipeline, row)
    env_class = _environment_class(row.environment_id) or "unknown"
    inc("cloudops_pipeline_runs_total", {"provider": provider_row.key, "status": row.status.lower(), "environment_class": env_class})
    if row.status == FAILED:
        inc("cloudops_pipeline_runs_failed_total", {"provider": provider_row.key, "status": "failed", "environment_class": env_class})
    return row


def upsert_stage(session: Session, run: PipelineRunRow, provider_key: str, item) -> PipelineStageRow:
    row_id = _id("pstg", run.id, item.external_id)
    row = session.get(PipelineStageRow, row_id)
    if row is None:
        row = PipelineStageRow(id=row_id, run_id=run.id, external_id=item.external_id, name=item.name)
        session.add(row)
    row.name = item.name
    row.provider_status = f"{item.status}:{item.result}".strip(":")
    row.status = normalize_run(provider_key, item.status, item.result)
    row.started_at = item.started_at
    row.completed_at = item.completed_at
    row.duration_seconds = duration_seconds(item.started_at, item.completed_at)
    row.sort_order = item.sort_order
    row.html_url = item.html_url
    return row


def upsert_job(session: Session, run: PipelineRunRow, provider_key: str, item, stages: dict[str, PipelineStageRow]) -> PipelineJobRow:
    row_id = _id("pjob", run.id, item.external_id)
    row = session.get(PipelineJobRow, row_id)
    if row is None:
        row = PipelineJobRow(id=row_id, run_id=run.id, external_id=item.external_id, name=item.name)
        session.add(row)
    row.name = item.name
    row.provider_status = f"{item.status}:{item.result}".strip(":")
    row.status = normalize_run(provider_key, item.status, item.result)
    row.started_at = item.started_at
    row.completed_at = item.completed_at
    row.duration_seconds = duration_seconds(item.started_at, item.completed_at)
    row.html_url = item.html_url
    stage = stages.get(item.stage_external_id) or next(iter(stages.values()), None)
    row.stage_id = stage.id if stage else ""
    return row


def _mark_provider(session: Session, row: PipelineProviderRow, *, ok: bool, error: str = "") -> None:
    row.last_attempted_sync_at = utcnow()
    if ok:
        row.last_successful_sync_at = utcnow()
        row.last_error = ""
        row.last_error_class = ""
        row.status = "ok"
    else:
        row.last_error = sanitize_text(error)[:1000]
        row.last_error_class = error.split(":")[0][:64] if error else "error"
        row.status = "error"
    row.updated_at = utcnow()


def _finish_job(session: Session, job_id: str | None, detail: str, status: str = "succeeded") -> None:
    if not job_id:
        return
    InventoryRepository(session).mark_job_finished(job_id, status=status, detail=detail)


def _sync_each_provider(session: Session, callback) -> tuple[int, list[str]]:
    provider_rows = ensure_provider_rows(session)
    adapters = list(get_pipeline_providers(session))
    count = 0
    errors: list[str] = []
    for adapter in adapters:
        row = provider_rows.get(adapter.key)
        if row is None:
            continue
        started = utcnow()
        try:
            count += int(callback(session, row, adapter) or 0)
            _mark_provider(session, row, ok=True)
            inc("cloudops_pipeline_sync_failures_total", {"provider": adapter.key, "status": "succeeded", "environment_class": "n/a"}, amount=0)
        except Exception as error:
            logger.exception("Pipeline provider isolated failure provider=%s", adapter.key)
            _mark_provider(session, row, ok=False, error=f"{type(error).__name__}: {error}")
            errors.append(adapter.key)
            inc("cloudops_pipeline_sync_failures_total", {"provider": adapter.key, "status": "failed", "environment_class": "n/a"})
        observe_duration(
            "cloudops_pipeline_sync_duration_seconds",
            {"provider": adapter.key, "status": "failed" if adapter.key in errors else "succeeded", "environment_class": "n/a"},
            (utcnow() - started).total_seconds(),
        )
    return count, errors


def run_provider_sync(job_id: str | None = None) -> int:
    session = SessionLocal()
    started = utcnow()
    try:
        ensure_provider_rows(session)
        session.commit()
        _finish_job(session, job_id, "pipeline-provider-sync")
        session.commit()
        return 1
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        observe_duration("cloudops_pipeline_sync_duration_seconds", {"provider": "all", "status": "provider", "environment_class": "n/a"}, (utcnow() - started).total_seconds())
        session.close()


def _sync_pipelines(session: Session, provider_row: PipelineProviderRow, adapter: PipelineProvider) -> int:
    count = 0
    for item in adapter.list_pipelines():
        upsert_pipeline(session, provider_row, item)
        count += 1
    session.flush()
    return count


def run_pipeline_sync(job_id: str | None = None) -> int:
    session = SessionLocal()
    try:
        count, errors = _sync_each_provider(session, _sync_pipelines)
        session.commit()
        _finish_job(
            session,
            job_id,
            f"pipeline-sync: {count} pipelines errors={','.join(errors)}",
            status="succeeded",
        )
        session.commit()
        return count
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        session.close()


def _sync_runs(session: Session, provider_row: PipelineProviderRow, adapter: PipelineProvider, *, running_only: bool, details: bool) -> int:
    count = 0
    pipelines = list(session.scalars(select(PipelineRow).where(PipelineRow.provider_id == provider_row.id)))
    since = None
    if not running_only:
        since = utcnow().replace(hour=0, minute=0, second=0, microsecond=0) if False else None
    for pipeline in pipelines:
        source = adapter.get_pipeline(pipeline.external_id) or ProviderPipeline(
            external_id=pipeline.external_id,
            name=pipeline.name,
            html_url=pipeline.html_url,
        )
        try:
            runs = adapter.list_runs(source, since=since, running_only=running_only)
        except Exception:
            logger.info("Run listing skipped pipeline=%s provider=%s", pipeline.id, provider_row.key)
            continue
        for item in runs:
            completed = item.completed_at
            if completed is not None and completed.tzinfo is None:
                completed = completed.replace(tzinfo=utcnow().tzinfo)
            if not running_only and completed is not None and (utcnow() - completed).days > settings.pipeline_run_retention_days:
                continue
            row = upsert_run(session, provider_row, pipeline, item)
            count += 1
            if details or row.status == RUNNING:
                try:
                    stages = {}
                    for stage in adapter.list_stages(item):
                        stages[stage.external_id] = upsert_stage(session, row, provider_row.key, stage)
                    for job in adapter.list_jobs(item):
                        upsert_job(session, row, provider_row.key, job, stages)
                except Exception:
                    logger.info("Run detail skipped run=%s", item.external_id)
    session.flush()
    running = list(session.scalars(select(PipelineRunRow).where(PipelineRunRow.status == RUNNING)))
    set_gauge(
        "cloudops_pipeline_runs_running",
        {"provider": provider_row.key, "status": "running", "environment_class": "n/a"},
        float(len(running)),
    )
    return count


def run_pipeline_run_sync(job_id: str | None = None, *, running_only: bool = False, details: bool = False) -> int:
    session = SessionLocal()
    try:
        count, errors = _sync_each_provider(
            session,
            lambda sess, row, adapter: _sync_runs(sess, row, adapter, running_only=running_only, details=details),
        )
        session.commit()
        _finish_job(session, job_id, f"pipeline-run-sync: {count} runs errors={','.join(errors)}")
        session.commit()
        return count
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        session.close()


def run_pipeline_run_detail_sync(job_id: str | None = None) -> int:
    return run_pipeline_run_sync(job_id, running_only=True, details=True)


def run_pipeline_retention(job_id: str | None = None) -> int:
    session = SessionLocal()
    try:
        now = utcnow()
        deleted = 0
        open_run_ids = {row.run_id for row in session.scalars(select(PipelineAlertRow).where(PipelineAlertRow.status == "OPEN"))}
        for run in list(session.scalars(select(PipelineRunRow))):
            stamp = run.completed_at or run.updated_at
            if stamp is None:
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=now.tzinfo)
            age_days = (now - stamp).days
            if age_days >= settings.pipeline_detail_retention_days and run.status not in {RUNNING}:
                for job in list(session.scalars(select(PipelineJobRow).where(PipelineJobRow.run_id == run.id))):
                    session.delete(job)
                    deleted += 1
                for stage in list(session.scalars(select(PipelineStageRow).where(PipelineStageRow.run_id == run.id))):
                    session.delete(stage)
                    deleted += 1
            if (
                age_days >= settings.pipeline_run_retention_days
                and not run.deployment_id
                and run.id not in open_run_ids
                and run.status not in {RUNNING}
            ):
                session.delete(run)
                deleted += 1
        session.commit()
        _finish_job(session, job_id, f"pipeline-retention: {deleted}")
        session.commit()
        return deleted
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        session.close()


def project_github_run(session: Session, github_run) -> PipelineRunRow | None:
    from app.db.models import GithubWorkflowRow
    from app.integrations.pipelines.github import GitHubActionsPipelineProvider

    workflow = session.get(GithubWorkflowRow, github_run.workflow_id)
    if workflow is None:
        return None
    providers = ensure_provider_rows(session)
    provider_row = providers["github-actions"]
    adapter = GitHubActionsPipelineProvider(session)
    pipeline = upsert_pipeline(session, provider_row, adapter._pipeline(workflow))
    source_run = adapter._run(github_run)
    run = upsert_run(session, provider_row, pipeline, source_run)
    stages = {}
    for stage in adapter.list_stages(source_run):
        stages[stage.external_id] = upsert_stage(session, run, provider_row.key, stage)
    for item in adapter.list_jobs(source_run):
        upsert_job(session, run, provider_row.key, item, stages)
    return run
