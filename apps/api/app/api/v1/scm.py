from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.config import settings
from app.core.rbac import Principal, principal_from_headers, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.db.models import (
    GithubEnvironmentMappingRow,
    GithubOrganizationRow,
    GithubRepositoryRow,
    GithubSecretRow,
    GithubVariableRow,
    GithubWorkflowJobRow,
    GithubWorkflowRunRow,
    GithubWorkflowRow,
)
from app.db.session import SessionLocal
from app.services.github_presenters import (
    environment_label,
    job_dump,
    organization_dump,
    overview_dump,
    repository_dump,
    run_dump,
    secret_dump,
    variable_dump,
    workflow_dump,
)
from app.services.github_secrets import delete_secret, delete_variable, replace_secret, upsert_variable
from app.services.github_sync import _id, ensure_application_link, record_audit, utcnow
from app.services.github_webhooks import accept_webhook
from app.services.job_kinds import (
    KIND_GITHUB_REPOSITORY_SYNC,
    KIND_GITHUB_SECRET_SYNC,
    KIND_GITHUB_VARIABLE_SYNC,
    KIND_GITHUB_WORKFLOW_RUN_SYNC,
    KIND_GITHUB_WORKFLOW_SYNC,
)
from app.services.jobs import enqueue_job
from app.integrations.github.exceptions import GitHubWebhookError

router = APIRouter()


class SecretWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repositoryId: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    value: str | None = Field(default=None, max_length=65536)
    scope: str = Field(default="repository", max_length=32)
    githubEnvironment: str = Field(default="", max_length=128)
    confirmed: bool = False
    reason: str = Field(default="", max_length=500)
    changeTicket: str = Field(default="", max_length=128)


class VariableWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repositoryId: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    value: str | None = Field(default=None, max_length=65536)
    scope: str = Field(default="repository", max_length=32)
    githubEnvironment: str = Field(default="", max_length=128)
    sensitive: bool = False
    confirmed: bool = False
    reason: str = Field(default="", max_length=500)


class MappingWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    githubRepositoryId: str
    githubEnvironment: str
    cloudopsEnvironmentId: str
    active: bool = True


class ApplicationLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repositoryId: str
    applicationId: str


def _dump(payload) -> dict:
    data = payload if isinstance(payload, dict) else payload.model_dump()
    assert_no_secret_values(walk_strings(data))
    data.pop("secretValue", None)
    return data


def _listed(items: list[dict]) -> dict:
    payload = {"items": items, "lastSynced": settings.last_synced}
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.get("/scm/overview")
def scm_overview(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        payload = overview_dump(session)
        payload["lastSynced"] = settings.last_synced
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()


@router.get("/scm/organizations")
def list_organizations(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubOrganizationRow)))
        return _listed([organization_dump(row) for row in rows])
    finally:
        session.close()


@router.get("/scm/repositories")
def list_repositories(
    organization: str | None = Query(default=None),
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubRepositoryRow)))
        if organization:
            rows = [row for row in rows if row.organization.lower() == organization.lower()]
        return _listed([repository_dump(session, row) for row in rows])
    finally:
        session.close()


@router.get("/scm/repositories/{repository_id}")
def get_repository(repository_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        row = session.get(GithubRepositoryRow, repository_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Repository not found")
        payload = repository_dump(session, row)
        payload["lastSynced"] = settings.last_synced
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()


@router.get("/scm/repositories/{repository_id}/workflows")
def list_repository_workflows(repository_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubWorkflowRow).where(GithubWorkflowRow.repository_id == repository_id)))
        return _listed([workflow_dump(session, row) for row in rows])
    finally:
        session.close()


@router.get("/scm/workflows")
def list_workflows(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubWorkflowRow)))
        return _listed([workflow_dump(session, row) for row in rows])
    finally:
        session.close()


@router.get("/scm/workflows/{workflow_id}")
def get_workflow(workflow_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        row = session.get(GithubWorkflowRow, workflow_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        payload = workflow_dump(session, row)
        payload["lastSynced"] = settings.last_synced
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()


@router.get("/scm/workflows/{workflow_id}/runs")
def list_workflow_runs(workflow_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        rows = list(
            session.scalars(
                select(GithubWorkflowRunRow)
                .where(GithubWorkflowRunRow.workflow_id == workflow_id)
                .order_by(GithubWorkflowRunRow.started_at.desc())
            )
        )
        return _listed([run_dump(session, row) for row in rows])
    finally:
        session.close()


@router.get("/scm/workflow-runs")
def list_runs(
    status: str | None = Query(default=None),
    repository_id: str | None = Query(default=None),
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubWorkflowRunRow).order_by(GithubWorkflowRunRow.started_at.desc())))
        if status:
            rows = [row for row in rows if row.status.lower() == status.lower()]
        if repository_id:
            rows = [row for row in rows if row.repository_id == repository_id]
        return _listed([run_dump(session, row) for row in rows])
    finally:
        session.close()


@router.get("/scm/workflow-runs/{run_id}")
def get_run(run_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        row = session.get(GithubWorkflowRunRow, run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Workflow run not found")
        payload = run_dump(session, row) or {}
        jobs = list(session.scalars(select(GithubWorkflowJobRow).where(GithubWorkflowJobRow.run_id == row.id)))
        payload["jobs"] = [job_dump(job) for job in jobs]
        payload["lastSynced"] = settings.last_synced
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()


@router.get("/scm/workflow-runs/{run_id}/jobs")
def list_run_jobs(run_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubWorkflowJobRow).where(GithubWorkflowJobRow.run_id == run_id)))
        return _listed([job_dump(row) for row in rows])
    finally:
        session.close()


@router.get("/scm/variables")
def list_variables(
    repository_id: str | None = Query(default=None),
    organization: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    github_environment: str | None = Query(default=None, alias="environment"),
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "github_variable:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubVariableRow)))
        if repository_id:
            rows = [row for row in rows if row.repository_id == repository_id]
        if organization:
            rows = [row for row in rows if row.organization.lower() == organization.lower()]
        if scope:
            rows = [row for row in rows if row.scope == scope]
        if github_environment:
            rows = [row for row in rows if row.github_environment.lower() == github_environment.lower()]
        return _listed([variable_dump(session, row) for row in rows])
    finally:
        session.close()


@router.post("/scm/variables")
def create_variable(body: VariableWriteRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github_variable:update")
    row = upsert_variable(
        principal,
        repository_id=body.repositoryId or "",
        name=body.name or "",
        value=body.value or "",
        scope=body.scope,
        github_environment=body.githubEnvironment,
        sensitive=body.sensitive,
        confirmed=body.confirmed,
        reason=body.reason,
        create=True,
    )
    session = SessionLocal()
    try:
        return _dump(variable_dump(session, session.get(GithubVariableRow, row.id)))
    finally:
        session.close()


@router.put("/scm/variables/{variable_id}")
def update_variable(
    variable_id: str, body: VariableWriteRequest, principal: Principal = Depends(principal_from_headers)
) -> dict:
    require_permission(principal, "github_variable:update")
    session = SessionLocal()
    try:
        existing = session.get(GithubVariableRow, variable_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="GitHub variable not found")
        repo_id = existing.repository_id
        name = existing.name
        scope = existing.scope
        env = existing.github_environment
    finally:
        session.close()
    row = upsert_variable(
        principal,
        repository_id=repo_id,
        name=name,
        value=body.value or "",
        scope=scope,
        github_environment=env,
        sensitive=body.sensitive,
        confirmed=body.confirmed,
        reason=body.reason,
    )
    session = SessionLocal()
    try:
        return _dump(variable_dump(session, session.get(GithubVariableRow, row.id)))
    finally:
        session.close()


@router.delete("/scm/variables/{variable_id}")
def remove_variable(variable_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github_variable:update")
    delete_variable(principal, variable_id=variable_id)
    return {"deleted": True}


@router.get("/scm/secrets")
def list_secrets(
    repository_id: str | None = Query(default=None),
    organization: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    github_environment: str | None = Query(default=None, alias="environment"),
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "github_secret:read_metadata")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubSecretRow)))
        if repository_id:
            rows = [row for row in rows if row.repository_id == repository_id]
        if organization:
            rows = [row for row in rows if row.organization.lower() == organization.lower()]
        if scope:
            rows = [row for row in rows if row.scope == scope]
        if github_environment:
            rows = [row for row in rows if row.github_environment.lower() == github_environment.lower()]
        return _listed([secret_dump(session, row) for row in rows])
    finally:
        session.close()


@router.post("/scm/secrets")
def create_secret(body: SecretWriteRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github_secret:create")
    row = replace_secret(
        principal,
        repository_id=body.repositoryId or "",
        name=body.name or "",
        value=body.value or "",
        scope=body.scope,
        github_environment=body.githubEnvironment,
        confirmed=body.confirmed,
        reason=body.reason,
        change_ticket=body.changeTicket,
        create=True,
    )
    session = SessionLocal()
    try:
        return _dump(secret_dump(session, session.get(GithubSecretRow, row.id)))
    finally:
        session.close()


@router.put("/scm/secrets/{secret_id}")
def update_secret(secret_id: str, body: SecretWriteRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github_secret:update")
    session = SessionLocal()
    try:
        existing = session.get(GithubSecretRow, secret_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="GitHub secret metadata not found")
        repo_id = existing.repository_id
        name = existing.name
        scope = existing.scope
        env = existing.github_environment
    finally:
        session.close()
    row = replace_secret(
        principal,
        repository_id=repo_id,
        name=name,
        value=body.value or "",
        scope=scope,
        github_environment=env,
        confirmed=body.confirmed,
        reason=body.reason,
        change_ticket=body.changeTicket,
    )
    session = SessionLocal()
    try:
        return _dump(secret_dump(session, session.get(GithubSecretRow, row.id)))
    finally:
        session.close()


@router.delete("/scm/secrets/{secret_id}")
def remove_secret(
    secret_id: str,
    body: SecretWriteRequest | None = None,
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "github_secret:delete")
    payload = body or SecretWriteRequest()
    delete_secret(principal, secret_id=secret_id, confirmed=payload.confirmed, reason=payload.reason)
    return {"deleted": True}


@router.post("/scm/environment-mappings")
def create_mapping(body: MappingWriteRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github_mapping:update")
    session = SessionLocal()
    try:
        row_id = _id("ghem", body.githubRepositoryId, body.githubEnvironment)
        row = session.get(GithubEnvironmentMappingRow, row_id)
        created = row is None
        if row is None:
            row = GithubEnvironmentMappingRow(
                id=row_id,
                github_repository_id=body.githubRepositoryId,
                github_environment=body.githubEnvironment,
                cloudops_environment_id=body.cloudopsEnvironmentId,
                active=body.active,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            session.add(row)
        else:
            row.cloudops_environment_id = body.cloudopsEnvironmentId
            row.active = body.active
            row.updated_at = utcnow()
        record_audit(
            session,
            "GITHUB_ENVIRONMENT_MAPPING_CHANGED",
            actor=principal.user,
            object_name=body.githubEnvironment,
            repository_id=body.githubRepositoryId,
        )
        session.commit()
        return {"id": row.id, "created": created}
    finally:
        session.close()


@router.get("/scm/environment-mappings")
def list_mappings(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github_mapping:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(GithubEnvironmentMappingRow)))
        items = []
        for row in rows:
            items.append(
                {
                    "id": row.id,
                    "githubRepositoryId": row.github_repository_id,
                    "githubEnvironment": row.github_environment,
                    "active": row.active,
                    **environment_label(session, row.cloudops_environment_id),
                }
            )
        return _listed(items)
    finally:
        session.close()


@router.post("/scm/application-repositories")
def link_application(body: ApplicationLinkRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github_mapping:update")
    session = SessionLocal()
    try:
        repo = session.get(GithubRepositoryRow, body.repositoryId)
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found")
        link = ensure_application_link(session, body.repositoryId, body.applicationId)
        record_audit(
            session,
            "GITHUB_ENVIRONMENT_MAPPING_CHANGED",
            actor=principal.user,
            object_name=body.applicationId,
            repository_id=body.repositoryId,
            detail="application repository association",
        )
        session.commit()
        return {"id": link.id, "repositoryId": link.repository_id, "applicationId": link.application_id}
    finally:
        session.close()


@router.post("/scm/sync")
def trigger_sync(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "github:sync")
    from app.services.mappers import to_job_record

    jobs = []
    for kind in (
        KIND_GITHUB_REPOSITORY_SYNC,
        KIND_GITHUB_WORKFLOW_SYNC,
        KIND_GITHUB_WORKFLOW_RUN_SYNC,
        KIND_GITHUB_VARIABLE_SYNC,
        KIND_GITHUB_SECRET_SYNC,
    ):
        row = enqueue_job(kind)
        jobs.append(to_job_record(row).model_dump())
    payload = {"queued": True, "jobs": jobs, "id": jobs[0]["id"] if jobs else ""}
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.post("/integrations/github/webhook")
async def github_webhook(request: Request) -> dict:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    try:
        accepted = accept_webhook(headers, body)
    except GitHubWebhookError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if accepted.get("queued"):
        from app.services.job_kinds import KIND_GITHUB_WEBHOOK
        from app.services.jobs import enqueue_job

        enqueue_job(KIND_GITHUB_WEBHOOK, target_id=accepted["id"])
    return accepted
