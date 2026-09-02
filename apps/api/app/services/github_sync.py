from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.correlation import current_correlation_id
from app.core.logging import get_logger, sanitize_text
from app.core.metrics import inc, observe_duration
from app.db.models import (
    CloudEnvironmentRow,
    GithubAlertRow,
    GithubApplicationRepositoryRow,
    GithubAuditRow,
    GithubEnvironmentMappingRow,
    GithubIntegrationRow,
    GithubOrganizationRow,
    GithubRepositoryRow,
    GithubSecretRow,
    GithubVariableRow,
    GithubWorkflowJobRow,
    GithubWorkflowRunRow,
    GithubWorkflowRow,
)
from app.db.repository import InventoryRepository, utcnow
from app.db.session import SessionLocal
from app.integrations.github.exceptions import GitHubNotConfigured
from app.integrations.github.mapper import duration_seconds, normalize_run_status
from app.integrations.github import get_scm_provider
from app.integrations.scm.base import ScmRepository, SourceControlProvider

logger = get_logger(__name__)
MASK = "••••••••••••"

ALERT_SEVERITY = {
    "DEV": "",
    "INT/TST": "",
    "UAT": "MEDIUM",
    "NPD": "HIGH",
    "PRD": "CRITICAL",
}


def _id(prefix: str, *parts: str) -> str:
    digest = sha256("|".join(parts).encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


def ensure_integration(session: Session) -> GithubIntegrationRow | None:
    row = session.scalar(select(GithubIntegrationRow).limit(1))
    if row is not None:
        return row
    if not settings.github_app_id or not settings.github_installation_id or not settings.github_private_key_ref:
        return None
    now = utcnow()
    row = GithubIntegrationRow(
        id=_id("ghi", settings.github_app_id, settings.github_installation_id),
        app_id=settings.github_app_id,
        installation_id=settings.github_installation_id,
        organization=settings.github_organization,
        api_url=settings.github_api_url,
        private_key_ref=settings.github_private_key_ref,
        webhook_secret_ref=settings.github_webhook_secret_ref,
        status="configured",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return row


def record_audit(
    session: Session,
    action: str,
    *,
    actor: str,
    object_name: str = "",
    repository_id: str = "",
    environment: str = "",
    result: str = "succeeded",
    detail: str = "",
) -> None:
    session.add(
        GithubAuditRow(
            id=str(uuid4()),
            action=action,
            actor=actor,
            object_name=object_name,
            repository_id=repository_id,
            environment=environment,
            result=result,
            detail=sanitize_text(detail)[:1000],
            correlation_id=current_correlation_id(),
            created_at=utcnow(),
        )
    )


def _environment_class(environment_id: str | None) -> str:
    environment_id = environment_id or ""
    if environment_id.endswith("-prd") or environment_id.endswith("/prd") or environment_id.endswith("prd"):
        return "PRD"
    if "-npd" in environment_id or environment_id.endswith("npd"):
        return "NPD"
    if "-uat" in environment_id:
        return "UAT"
    if "int" in environment_id or "tst" in environment_id:
        return "INT/TST"
    if environment_id.endswith("-dev") or environment_id.endswith("dev"):
        return "DEV"
    return ""


def mapped_environment(session: Session, repository_id: str, github_environment: str) -> CloudEnvironmentRow | None:
    mapping = session.scalar(
        select(GithubEnvironmentMappingRow).where(
            GithubEnvironmentMappingRow.github_repository_id == repository_id,
            GithubEnvironmentMappingRow.github_environment == github_environment,
            GithubEnvironmentMappingRow.active.is_(True),
        )
    )
    if mapping is None:
        return None
    return session.get(CloudEnvironmentRow, mapping.cloudops_environment_id)


def upsert_organization(session: Session, integration: GithubIntegrationRow, org) -> GithubOrganizationRow:
    row_id = _id("gho", org.external_id)
    row = session.get(GithubOrganizationRow, row_id)
    if row is None:
        row = GithubOrganizationRow(id=row_id, integration_id=integration.id, github_id=org.external_id, login=org.login)
        session.add(row)
    row.name = org.name or org.login
    row.avatar_url = org.avatar_url
    row.html_url = org.html_url
    row.status = "ok"
    row.last_synchronized_at = utcnow()
    return row


def upsert_repository(session: Session, org: GithubOrganizationRow, repo: ScmRepository) -> GithubRepositoryRow:
    row_id = _id("ghr", repo.external_id)
    row = session.get(GithubRepositoryRow, row_id)
    if row is None:
        row = GithubRepositoryRow(
            id=row_id,
            organization_id=org.id,
            github_id=repo.external_id,
            organization=repo.organization,
            name=repo.name,
            full_name=repo.full_name,
        )
        session.add(row)
    row.description = repo.description
    row.default_branch = repo.default_branch
    row.visibility = repo.visibility
    row.archived = repo.archived
    row.html_url = repo.html_url
    row.pushed_at = repo.pushed_at
    row.last_synchronized_at = utcnow()
    row.organization = repo.organization or org.login
    row.name = repo.name
    row.full_name = repo.full_name
    auto_link_applications(session, row)
    return row


def ensure_application_link(session: Session, repository_id: str, application_id: str) -> GithubApplicationRepositoryRow:
    row_id = _id("ghar", repository_id, application_id)
    row = session.get(GithubApplicationRepositoryRow, row_id)
    if row is None:
        row = GithubApplicationRepositoryRow(
            id=row_id,
            repository_id=repository_id,
            application_id=application_id,
            created_at=utcnow(),
        )
        session.add(row)
    return row


def auto_link_applications(session: Session, repo: GithubRepositoryRow) -> None:
    try:
        from app.data.inventory import MOCK_INVENTORY
    except Exception:
        return
    for app in MOCK_INVENTORY.applications:
        if app.name.lower() == repo.name.lower():
            ensure_application_link(session, repo.id, app.id)


def upsert_workflow(session: Session, repository: GithubRepositoryRow, workflow) -> GithubWorkflowRow:
    row_id = _id("ghw", workflow.external_id)
    row = session.get(GithubWorkflowRow, row_id)
    if row is None:
        row = GithubWorkflowRow(
            id=row_id,
            repository_id=repository.id,
            github_id=workflow.external_id,
            name=workflow.name,
            path=workflow.path,
        )
        session.add(row)
    row.name = workflow.name
    row.path = workflow.path
    row.state = workflow.state
    row.html_url = workflow.html_url
    row.created_at = workflow.created_at
    row.updated_at = workflow.updated_at
    row.last_synchronized_at = utcnow()
    return row


def correlate_run(session: Session, repository: GithubRepositoryRow, run_row: GithubWorkflowRunRow) -> None:
    mapping = None
    if run_row.github_environment:
        mapping = mapped_environment(session, repository.id, run_row.github_environment)
    if mapping is not None:
        run_row.cloudops_environment_id = mapping.id
        run_row.cluster_id = ""
    link = session.scalar(
        select(GithubApplicationRepositoryRow).where(GithubApplicationRepositoryRow.repository_id == repository.id)
    )
    if link is not None:
        run_row.application_id = link.application_id
    if run_row.commit_sha:
        run_row.deployment_id = _id("ghd", run_row.repository_id, run_row.commit_sha, run_row.github_id)


def upsert_run(session: Session, repository: GithubRepositoryRow, workflow: GithubWorkflowRow, run) -> GithubWorkflowRunRow:
    row_id = _id("ghrun", run.external_id)
    row = session.get(GithubWorkflowRunRow, row_id)
    created = row is None
    if row is None:
        row = GithubWorkflowRunRow(
            id=row_id,
            workflow_id=workflow.id,
            repository_id=repository.id,
            github_id=run.external_id,
        )
        session.add(row)
    row.branch = run.branch
    row.commit_sha = run.commit_sha
    row.event = run.event
    row.actor = run.actor
    row.github_status = run.status
    row.github_conclusion = run.conclusion
    row.status = normalize_run_status(run.status, run.conclusion)
    row.started_at = run.started_at
    row.completed_at = run.completed_at
    row.duration_seconds = duration_seconds(run.started_at, run.completed_at)
    row.run_attempt = run.run_attempt
    row.html_url = run.html_url
    row.github_environment = run.github_environment
    correlate_run(session, repository, row)
    if created:
        evaluate_run_alert(session, repository, workflow, row)
    else:
        evaluate_run_alert(session, repository, workflow, row)
    try:
        from app.services.pipeline_sync import project_github_run

        project_github_run(session, row)
    except Exception:
        logger.info("Pipeline projection skipped for GitHub run=%s", row.id)
    return row


def upsert_job(session: Session, run: GithubWorkflowRunRow, job) -> GithubWorkflowJobRow:
    row_id = _id("ghjob", job.external_id)
    row = session.get(GithubWorkflowJobRow, row_id)
    if row is None:
        row = GithubWorkflowJobRow(id=row_id, run_id=run.id, github_id=job.external_id, name=job.name)
        session.add(row)
    row.name = job.name
    row.github_status = job.status
    row.github_conclusion = job.conclusion
    row.status = normalize_run_status(job.status, job.conclusion)
    row.started_at = job.started_at
    row.completed_at = job.completed_at
    row.duration_seconds = duration_seconds(job.started_at, job.completed_at)
    row.runner_name = job.runner_name
    row.runner_type = job.runner_group
    row.html_url = job.html_url
    return row


def evaluate_run_alert(
    session: Session,
    repository: GithubRepositoryRow,
    workflow: GithubWorkflowRow,
    run: GithubWorkflowRunRow,
) -> None:
    env_row = session.get(CloudEnvironmentRow, run.cloudops_environment_id) if run.cloudops_environment_id else None
    environment = env_row.environment if env_row else ""
    configured = {
        "DEV": settings.github_alert_dev,
        "INT/TST": settings.github_alert_int_tst,
        "UAT": settings.github_alert_uat,
        "NPD": settings.github_alert_npd,
        "PRD": settings.github_alert_prd,
    }
    severity = (configured.get(environment) if environment else "") or ""
    existing = session.scalar(
        select(GithubAlertRow).where(GithubAlertRow.run_id == run.id, GithubAlertRow.status == "OPEN")
    )
    if run.status != "FAILED" or not severity:
        if existing is not None and run.status == "SUCCEEDED":
            existing.status = "RESOLVED"
            existing.resolved_at = utcnow()
            existing.last_evaluated_at = utcnow()
            from app.alerting.publishers import publish_github

            publish_github(session, repository=repository, workflow=workflow, run=run, environment=environment, severity=severity or "MEDIUM", recovered=True, env_row=env_row)
        return
    if existing is not None:
        existing.last_evaluated_at = utcnow()
        existing.severity = severity
        return
    session.add(
        GithubAlertRow(
            id=_id("gha", run.id),
            kind="GITHUB_WORKFLOW_FAILED",
            run_id=run.id,
            repository_id=repository.id,
            workflow_id=workflow.id,
            environment=environment,
            severity=severity,
            status="OPEN",
            title=f"{workflow.name} failed",
            created_at=utcnow(),
            last_evaluated_at=utcnow(),
        )
    )
    from app.alerting.publishers import publish_github

    publish_github(session, repository=repository, workflow=workflow, run=run, environment=environment, severity=severity, env_row=env_row)


def _finish_job(session: Session, job_id: str | None, detail: str, status: str = "succeeded") -> None:
    if not job_id:
        return
    repo = InventoryRepository(session)
    repo.mark_job_finished(job_id, status=status, detail=detail)


def run_repository_sync(job_id: str | None = None, *, provider: SourceControlProvider | None = None) -> int:
    started = utcnow()
    session = SessionLocal()
    try:
        integration = ensure_integration(session)
        if integration is None and provider is None:
            _finish_job(session, job_id, "github-repository-sync: GitHub App is not configured")
            session.commit()
            return 0
        scm = provider or get_scm_provider()
        count = 0
        orgs = scm.list_organizations()
        if integration is None:
            integration = ensure_integration(session)
        if integration is None:
            now = utcnow()
            integration = GithubIntegrationRow(
                id=_id("ghi", "test"),
                app_id="test",
                installation_id="test",
                organization="",
                api_url=settings.github_api_url,
                private_key_ref="local://github-app",
                created_at=now,
                updated_at=now,
                status="configured",
            )
            session.add(integration)
            session.flush()
        org_by_login: dict[str, GithubOrganizationRow] = {}
        for org in orgs:
            row = upsert_organization(session, integration, org)
            org_by_login[row.login] = row
        session.flush()
        for repo in scm.list_repositories():
            org = org_by_login.get(repo.organization)
            if org is None and orgs:
                org = upsert_organization(session, integration, orgs[0])
                org_by_login[org.login] = org
                session.flush()
            if org is None:
                continue
            upsert_repository(session, org, repo)
            count += 1
        integration.last_synchronized_at = utcnow()
        integration.status = "ok"
        integration.last_error = ""
        session.flush()
        _finish_job(session, job_id, f"github-repository-sync: {count} repositories")
        session.commit()
        inc("cloudops_github_sync_total", {"job": "repository", "status": "succeeded"})
        return count
    except GitHubNotConfigured:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, "github-repository-sync: GitHub App is not configured")
        session.commit()
        return 0
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        inc("cloudops_github_sync_failures_total", {"job": "repository", "status": "failed"})
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        observe_duration("cloudops_github_sync_duration_seconds", {"job": "repository"}, (utcnow() - started).total_seconds())
        session.close()


def run_workflow_sync(job_id: str | None = None, *, provider: SourceControlProvider | None = None) -> int:
    session = SessionLocal()
    try:
        scm = provider or get_scm_provider()
        count = 0
        repos = list(session.scalars(select(GithubRepositoryRow)))
        for repo in repos:
            scm_repo = ScmRepository(
                external_id=repo.github_id,
                organization=repo.organization,
                name=repo.name,
                full_name=repo.full_name,
            )
            for workflow in scm.list_workflows(scm_repo):
                upsert_workflow(session, repo, workflow)
                count += 1
        session.flush()
        _finish_job(session, job_id, f"github-workflow-sync: {count} workflows")
        session.commit()
        inc("cloudops_github_sync_total", {"job": "workflow", "status": "succeeded"})
        return count
    except GitHubNotConfigured:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, "github-workflow-sync: GitHub App is not configured")
        session.commit()
        return 0
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        inc("cloudops_github_sync_failures_total", {"job": "workflow", "status": "failed"})
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        session.close()


def run_workflow_run_sync(job_id: str | None = None, *, provider: SourceControlProvider | None = None) -> int:
    session = SessionLocal()
    try:
        scm = provider or get_scm_provider()
        count = 0
        repos = list(session.scalars(select(GithubRepositoryRow)))
        workflows = {row.github_id: row for row in session.scalars(select(GithubWorkflowRow))}
        for repo in repos:
            scm_repo = ScmRepository(
                external_id=repo.github_id,
                organization=repo.organization,
                name=repo.name,
                full_name=repo.full_name,
            )
            for run in scm.list_workflow_runs(scm_repo):
                workflow = workflows.get(run.workflow_external_id)
                if workflow is None:
                    workflow = upsert_workflow(
                        session,
                        repo,
                        type("W", (), {
                            "external_id": run.workflow_external_id or run.external_id,
                            "name": "workflow",
                            "path": "",
                            "state": "active",
                            "html_url": "",
                            "created_at": None,
                            "updated_at": None,
                        })(),
                    )
                    workflows[workflow.github_id] = workflow
                row = upsert_run(session, repo, workflow, run)
                try:
                    for job in scm.list_jobs(run, scm_repo):
                        upsert_job(session, row, job)
                except Exception:
                    logger.info("Job listing skipped for run=%s", run.external_id)
                inc("cloudops_github_workflow_runs_total", {"status": row.status.lower(), "environment_class": _environment_class(row.cloudops_environment_id) or "unknown"})
                if row.status == "FAILED":
                    inc("cloudops_github_workflow_failures_total", {"status": "failed", "environment_class": _environment_class(row.cloudops_environment_id) or "unknown"})
                count += 1
        session.flush()
        _finish_job(session, job_id, f"github-workflow-run-sync: {count} runs")
        session.commit()
        inc("cloudops_github_sync_total", {"job": "workflow_run", "status": "succeeded"})
        return count
    except GitHubNotConfigured:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, "github-workflow-run-sync: GitHub App is not configured")
        session.commit()
        return 0
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        inc("cloudops_github_sync_failures_total", {"job": "workflow_run", "status": "failed"})
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        session.close()


def run_variable_sync(job_id: str | None = None, *, provider: SourceControlProvider | None = None) -> int:
    session = SessionLocal()
    try:
        scm = provider or get_scm_provider()
        count = 0
        for repo in session.scalars(select(GithubRepositoryRow)):
            scm_repo = ScmRepository(
                external_id=repo.github_id,
                organization=repo.organization,
                name=repo.name,
                full_name=repo.full_name,
            )
            variables = list(scm.list_variables(scm_repo))
            org_lister = getattr(scm, "list_organization_variables", None)
            if callable(org_lister) and repo.organization:
                try:
                    variables.extend(org_lister(repo.organization))
                except Exception:
                    logger.info("Organization variable listing skipped org=%s", repo.organization)
            for variable in variables:
                owner = repo.id if variable.scope != "organization" else f"org:{variable.organization or repo.organization}"
                row_id = _id("ghvar", owner, variable.scope, variable.github_environment, variable.name)
                row = session.get(GithubVariableRow, row_id)
                if row is None:
                    row = GithubVariableRow(
                        id=row_id,
                        repository_id=repo.id,
                        name=variable.name,
                        scope=variable.scope,
                        github_environment=variable.github_environment,
                    )
                    session.add(row)
                row.organization = variable.organization or repo.organization
                row.sensitive = variable.sensitive or settings.github_variable_sensitive_default
                row.value_masked = MASK if row.sensitive else (variable.value[:48] if variable.value else "")
                row.updated_at = variable.updated_at or utcnow()
                mapped = mapped_environment(session, repo.id, variable.github_environment) if variable.github_environment else None
                row.cloudops_environment_id = mapped.id if mapped else ""
                count += 1
        session.flush()
        _finish_job(session, job_id, f"github-variable-sync: {count} variables")
        session.commit()
        inc("cloudops_github_sync_total", {"job": "variable", "status": "succeeded"})
        return count
    except GitHubNotConfigured:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, "github-variable-sync: GitHub App is not configured")
        session.commit()
        return 0
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        inc("cloudops_github_sync_failures_total", {"job": "variable", "status": "failed"})
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        session.close()


def run_secret_metadata_sync(job_id: str | None = None, *, provider: SourceControlProvider | None = None) -> int:
    session = SessionLocal()
    try:
        scm = provider or get_scm_provider()
        count = 0
        for repo in session.scalars(select(GithubRepositoryRow)):
            scm_repo = ScmRepository(
                external_id=repo.github_id,
                organization=repo.organization,
                name=repo.name,
                full_name=repo.full_name,
            )
            secrets = list(scm.list_secrets(scm_repo))
            org_lister = getattr(scm, "list_organization_secrets", None)
            if callable(org_lister) and repo.organization:
                try:
                    secrets.extend(org_lister(repo.organization))
                except Exception:
                    logger.info("Organization secret listing skipped org=%s", repo.organization)
            for secret in secrets:
                owner = repo.id if secret.scope != "organization" else f"org:{secret.organization or repo.organization}"
                row_id = _id("ghsec", owner, secret.scope, secret.github_environment, secret.name)
                row = session.get(GithubSecretRow, row_id)
                if row is None:
                    row = GithubSecretRow(
                        id=row_id,
                        repository_id=repo.id,
                        name=secret.name,
                        scope=secret.scope,
                        github_environment=secret.github_environment,
                    )
                    session.add(row)
                row.organization = secret.organization or repo.organization
                row.created_at = secret.created_at
                row.updated_at = secret.updated_at
                mapped = mapped_environment(session, repo.id, secret.github_environment) if secret.github_environment else None
                row.cloudops_environment_id = mapped.id if mapped else ""
                count += 1
        session.flush()
        _finish_job(session, job_id, f"github-secret-metadata-sync: {count} secrets")
        session.commit()
        inc("cloudops_github_sync_total", {"job": "secret_metadata", "status": "succeeded"})
        return count
    except GitHubNotConfigured:
        session.rollback()
        session = SessionLocal()
        _finish_job(session, job_id, "github-secret-metadata-sync: GitHub App is not configured")
        session.commit()
        return 0
    except Exception as error:
        session.rollback()
        session = SessionLocal()
        inc("cloudops_github_sync_failures_total", {"job": "secret_metadata", "status": "failed"})
        _finish_job(session, job_id, sanitize_text(str(error)), status="failed")
        session.commit()
        raise
    finally:
        session.close()
