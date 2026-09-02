from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.rbac import Principal, principal_from_headers, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.db.models import (
    PipelineApplicationMappingRow,
    PipelineEnvironmentMappingRow,
    PipelineJobRow,
    PipelineProviderRow,
    PipelineRow,
    PipelineRunRow,
    PipelineStageRow,
)
from app.db.session import SessionLocal
from app.integrations.pipelines.exceptions import PipelineWebhookError
from app.services.job_kinds import (
    KIND_PIPELINE_PROVIDER_SYNC,
    KIND_PIPELINE_RUN_DETAIL_SYNC,
    KIND_PIPELINE_RUN_SYNC,
    KIND_PIPELINE_SYNC,
    KIND_PIPELINE_WEBHOOK,
)
from app.services.jobs import enqueue_job
from app.services.pipeline_presenters import (
    job_dump,
    mapping_dump,
    overview_dump,
    pipeline_dump,
    provider_dump,
    run_dump,
    stage_dump,
)
from app.services.pipeline_sync import _id, ensure_provider_rows, record_audit, utcnow
from app.services.pipeline_webhooks import accept_azure_webhook

router = APIRouter()


class MappingWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environmentId: str
    branchPattern: str = "*"
    stageName: str = ""
    active: bool = True
    priority: int = 0


class ApplicationMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applicationId: str = Field(min_length=1, max_length=128)


def _payload(data: dict) -> dict:
    assert_no_secret_values(walk_strings(data))
    return data


def _matches(item: dict, *, provider: str | None, environment: str | None, application: str | None, status: str | None, branch: str | None) -> bool:
    if provider and (item.get("providerKey") or "").lower() != provider.lower():
        return False
    if environment and (item.get("environment") or "").lower() != environment.lower() and environment.lower() not in (item.get("environment") or "").lower():
        if environment.lower() not in {"int-tst", "int/tst"} or item.get("environment") != "INT/TST":
            return False
    if application:
        apps = item.get("applicationIds") or []
        if application not in apps and application != item.get("applicationId") and application.lower() not in (item.get("pipelineName") or item.get("name") or "").lower():
            return False
    if status and (item.get("status") or (item.get("latestRun") or {}).get("status") or "").lower() != status.lower():
        return False
    if branch and (item.get("branch") or item.get("defaultBranch") or "") != branch:
        latest = item.get("latestRun") or {}
        if latest.get("branch") != branch:
            return False
    return True


@router.get("/pipelines/overview")
def pipeline_overview(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        return _payload({**overview_dump(session), "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/pipelines")
def list_pipelines(
    principal: Principal = Depends(principal_from_headers),
    provider: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    application: str | None = Query(default=None),
    status: str | None = Query(default=None),
    branch: str | None = Query(default=None),
    region: str | None = Query(default=None),
) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        ensure_provider_rows(session)
        session.commit()
        items = [pipeline_dump(session, row) for row in session.scalars(select(PipelineRow))]
        if region:
            items = [item for item in items if (item.get("region") or "").lower() == region.lower()]
        items = [
            item
            for item in items
            if _matches(item, provider=provider, environment=environment, application=application, status=status, branch=branch)
        ]
        if items:
            return _payload({"items": items, "lastSynced": utcnow().isoformat()})
        from app.services.catalog import catalog_service
        from app.domain.models import Scope

        mocks = catalog_service._collect("list_pipelines")
        converted = [
            {
                "id": row.id,
                "name": row.name,
                "providerKey": "mock",
                "providerName": "Mock",
                "provider": row.provider,
                "region": row.region,
                "environment": row.environment,
                "repository": row.detail,
                "applicationId": "",
                "applicationIds": [],
                "defaultBranch": "",
                "branch": "",
                "latestRun": {
                    "id": row.id,
                    "status": "FAILED" if row.result == "Failed" else "SUCCEEDED" if row.result == "Succeeded" else "RUNNING",
                    "actor": "",
                    "age": row.age,
                    "durationSeconds": None,
                    "branch": "",
                },
                "htmlUrl": "",
                "enabled": True,
            }
            for row in mocks
        ]
        converted = [
            item
            for item in converted
            if _matches(item, provider=provider if provider not in {"github-actions", "azure-devops"} else None, environment=environment, application=application, status=status, branch=branch)
        ]
        return _payload({"items": converted, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/pipelines/{pipeline_id}")
def get_pipeline(pipeline_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        row = session.get(PipelineRow, pipeline_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return _payload(pipeline_dump(session, row))
    finally:
        session.close()


@router.get("/pipelines/{pipeline_id}/runs")
def list_pipeline_runs(
    pipeline_id: str,
    principal: Principal = Depends(principal_from_headers),
    status: str | None = Query(default=None),
) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        if session.get(PipelineRow, pipeline_id) is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        rows = list(session.scalars(select(PipelineRunRow).where(PipelineRunRow.pipeline_id == pipeline_id)))
        items = [run_dump(session, row) for row in rows]
        if status:
            items = [item for item in items if (item or {}).get("status", "").lower() == status.lower()]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/pipelines/{pipeline_id}/environment-mappings")
def list_mappings(pipeline_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline_mapping:read")
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(PipelineEnvironmentMappingRow).where(PipelineEnvironmentMappingRow.pipeline_id == pipeline_id)))
        return _payload({"items": [mapping_dump(session, row) for row in rows], "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.post("/pipelines/{pipeline_id}/environment-mappings")
def create_mapping(pipeline_id: str, body: MappingWriteRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline_mapping:update")
    session = SessionLocal()
    try:
        pipeline = session.get(PipelineRow, pipeline_id)
        if pipeline is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        row_id = _id("pem", pipeline_id, body.environmentId, body.branchPattern, body.stageName)
        row = session.get(PipelineEnvironmentMappingRow, row_id)
        created = row is None
        if row is None:
            row = PipelineEnvironmentMappingRow(
                id=row_id,
                pipeline_id=pipeline_id,
                environment_id=body.environmentId,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            session.add(row)
        row.branch_pattern = body.branchPattern
        row.stage_name = body.stageName
        row.active = body.active
        row.priority = body.priority
        row.updated_at = utcnow()
        record_audit(
            session,
            "PIPELINE_MAPPING_CREATED" if created else "PIPELINE_MAPPING_UPDATED",
            actor=principal.user,
            object_name=pipeline.name,
            pipeline_id=pipeline_id,
            environment=body.environmentId,
        )
        session.commit()
        session.refresh(row)
        return _payload(mapping_dump(session, row))
    finally:
        session.close()


@router.post("/pipelines/{pipeline_id}/application-mappings")
def create_app_mapping(pipeline_id: str, body: ApplicationMappingRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline_mapping:update")
    session = SessionLocal()
    try:
        pipeline = session.get(PipelineRow, pipeline_id)
        if pipeline is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        row_id = _id("pam", pipeline_id, body.applicationId)
        row = session.get(PipelineApplicationMappingRow, row_id)
        if row is None:
            row = PipelineApplicationMappingRow(
                id=row_id,
                pipeline_id=pipeline_id,
                application_id=body.applicationId,
                created_at=utcnow(),
            )
            session.add(row)
        pipeline.application_id = body.applicationId
        record_audit(
            session,
            "PIPELINE_MAPPING_UPDATED",
            actor=principal.user,
            object_name=pipeline.name,
            pipeline_id=pipeline_id,
            detail=f"application={body.applicationId}",
        )
        session.commit()
        return _payload({"id": row.id, "pipelineId": pipeline_id, "applicationId": body.applicationId})
    finally:
        session.close()


@router.delete("/pipeline-environment-mappings/{mapping_id}")
def delete_mapping(mapping_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline_mapping:update")
    session = SessionLocal()
    try:
        row = session.get(PipelineEnvironmentMappingRow, mapping_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Mapping not found")
        record_audit(
            session,
            "PIPELINE_MAPPING_DELETED",
            actor=principal.user,
            object_name=row.pipeline_id,
            pipeline_id=row.pipeline_id,
            environment=row.environment_id,
        )
        session.delete(row)
        session.commit()
        return _payload({"deleted": True})
    finally:
        session.close()


@router.get("/pipeline-runs")
def list_runs(
    principal: Principal = Depends(principal_from_headers),
    provider: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    application: str | None = Query(default=None),
    status: str | None = Query(default=None),
    branch: str | None = Query(default=None),
) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        items = [run_dump(session, row) for row in session.scalars(select(PipelineRunRow))]
        items = [
            item
            for item in items
            if item
            and _matches(item, provider=provider, environment=environment, application=application, status=status, branch=branch)
        ]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/pipeline-runs/{run_id}")
def get_run(run_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        row = session.get(PipelineRunRow, run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        payload = run_dump(session, row) or {}
        payload["stages"] = [
            stage_dump(item)
            for item in session.scalars(select(PipelineStageRow).where(PipelineStageRow.run_id == run_id).order_by(PipelineStageRow.sort_order))
        ]
        payload["jobs"] = [job_dump(item) for item in session.scalars(select(PipelineJobRow).where(PipelineJobRow.run_id == run_id))]
        return _payload(payload)
    finally:
        session.close()


@router.get("/pipeline-runs/{run_id}/stages")
def list_stages(run_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        if session.get(PipelineRunRow, run_id) is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        items = [
            stage_dump(item)
            for item in session.scalars(select(PipelineStageRow).where(PipelineStageRow.run_id == run_id).order_by(PipelineStageRow.sort_order))
        ]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/pipeline-runs/{run_id}/jobs")
def list_jobs(run_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        if session.get(PipelineRunRow, run_id) is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        items = [job_dump(item) for item in session.scalars(select(PipelineJobRow).where(PipelineJobRow.run_id == run_id))]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/pipeline-providers")
def list_providers(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline:read")
    session = SessionLocal()
    try:
        ensure_provider_rows(session)
        session.commit()
        items = [provider_dump(row) for row in session.scalars(select(PipelineProviderRow))]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.post("/pipelines/sync")
def trigger_sync(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "pipeline:sync")
    from app.services.mappers import to_job_record

    session = SessionLocal()
    try:
        record_audit(session, "PIPELINE_SYNC_TRIGGERED", actor=principal.user, object_name="pipelines")
        session.commit()
    finally:
        session.close()
    jobs = []
    for kind in (
        KIND_PIPELINE_PROVIDER_SYNC,
        KIND_PIPELINE_SYNC,
        KIND_PIPELINE_RUN_SYNC,
        KIND_PIPELINE_RUN_DETAIL_SYNC,
    ):
        jobs.append(to_job_record(enqueue_job(kind)).model_dump())
    return _payload({"queued": True, "jobs": jobs})


@router.post("/integrations/azure-devops/webhook")
async def azure_devops_webhook(request: Request) -> dict:
    body = await request.body()
    headers = {key: value for key, value in request.headers.items()}
    try:
        accepted = accept_azure_webhook(headers, body)
    except PipelineWebhookError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    if accepted.get("queued"):
        enqueue_job(KIND_PIPELINE_WEBHOOK, target_id=accepted["id"])
    return _payload(accepted)
