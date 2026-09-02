from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import select

from app.core.rbac import Principal, principal_from_headers, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.db.models import (
    ApplicationHealthRow,
    HealthCheckDefinitionRow,
    HealthCheckResultRow,
    HealthIncidentRow,
    HealthTimelineEventRow,
    ResourceHealthRow,
)
from app.db.session import SessionLocal
from app.services.job_kinds import (
    KIND_CLUSTER_HEALTH_SCAN,
    KIND_DEPENDENCY_HEALTH_CHECK,
    KIND_HEALTH_AGGREGATION,
    KIND_HTTP_HEALTH_CHECK,
)
from app.services.jobs import enqueue_job
from app.services.health_presenters import (
    application_dump,
    environment_health_dump,
    incident_dump,
    overview_dump,
    resource_dump,
    result_dump,
)
from app.services.health_sync import acknowledge_incident, record_audit
from app.services.mappers import to_job_record
from app.db.repository import utcnow

router = APIRouter()


def _payload(data: dict) -> dict:
    assert_no_secret_values(walk_strings(data))
    return data


def _matches(item: dict, *, provider: str | None, region: str | None, environment: str | None, status: str | None, application: str | None) -> bool:
    if provider and (item.get("provider") or "").lower() != provider.lower():
        return False
    if region and (item.get("region") or "").lower() != region.lower():
        return False
    if environment:
        env = (item.get("environment") or "").lower()
        needle = environment.lower()
        if needle not in env and not (needle in {"int-tst", "int/tst"} and item.get("environment") == "INT/TST"):
            return False
    if status and (item.get("status") or "").lower() != status.lower():
        return False
    if application:
        haystack = f"{item.get('applicationId') or ''} {item.get('name') or ''} {item.get('resourceName') or ''}".lower()
        if application.lower() not in haystack:
            return False
    return True


@router.get("/health/overview")
def health_overview(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "health:read")
    session = SessionLocal()
    try:
        return _payload(overview_dump(session))
    finally:
        session.close()


@router.get("/health/resources")
def list_resources(
    principal: Principal = Depends(principal_from_headers),
    provider: str | None = Query(default=None),
    region: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    status: str | None = Query(default=None),
    application: str | None = Query(default=None),
    cluster: str | None = Query(default=None),
    namespace: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
) -> dict:
    require_permission(principal, "health:read")
    session = SessionLocal()
    try:
        items = [resource_dump(session, row) for row in session.scalars(select(ResourceHealthRow))]
        if cluster:
            items = [item for item in items if item.get("clusterId") == cluster]
        if namespace:
            items = [item for item in items if (item.get("namespace") or "").lower() == namespace.lower()]
        if resource_type:
            items = [item for item in items if (item.get("resourceType") or "").lower() == resource_type.lower()]
        items = [
            item
            for item in items
            if _matches(item, provider=provider, region=region, environment=environment, status=status, application=application)
        ]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/health/applications")
def list_applications(
    principal: Principal = Depends(principal_from_headers),
    provider: str | None = Query(default=None),
    region: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    status: str | None = Query(default=None),
    application: str | None = Query(default=None),
) -> dict:
    require_permission(principal, "health:read")
    session = SessionLocal()
    try:
        items = [application_dump(session, row) for row in session.scalars(select(ApplicationHealthRow))]
        items = [
            item
            for item in items
            if _matches(item, provider=provider, region=region, environment=environment, status=status, application=application)
        ]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/health/applications/{application_id}")
def get_application(application_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "health:read")
    session = SessionLocal()
    try:
        row = session.get(ApplicationHealthRow, application_id)
        if row is None:
            row = session.scalar(select(ApplicationHealthRow).where(ApplicationHealthRow.application_id == application_id))
        if row is None:
            raise HTTPException(status_code=404, detail="Application health not found")
        return _payload(application_dump(session, row))
    finally:
        session.close()


@router.get("/health/applications/{application_id}/history")
def application_history(application_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "health:read")
    session = SessionLocal()
    try:
        results = [
            result_dump(row)
            for row in session.scalars(
                select(HealthCheckResultRow)
                .where(HealthCheckResultRow.application_id == application_id)
                .order_by(HealthCheckResultRow.created_at.desc())
            )
        ]
        timeline = [
            {
                "id": row.id,
                "eventType": row.event_type,
                "title": row.title,
                "detail": row.detail,
                "href": row.href,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
            }
            for row in session.scalars(
                select(HealthTimelineEventRow)
                .where(HealthTimelineEventRow.application_id == application_id)
                .order_by(HealthTimelineEventRow.created_at.asc())
            )
        ]
        return _payload({"items": results, "timeline": timeline, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/health/environments/{environment_id}")
def environment_health(environment_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "health:read")
    session = SessionLocal()
    try:
        return _payload(environment_health_dump(session, environment_id))
    finally:
        session.close()


@router.get("/health/incidents")
def list_incidents(
    principal: Principal = Depends(principal_from_headers),
    provider: str | None = Query(default=None),
    region: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    status: str | None = Query(default=None),
    application: str | None = Query(default=None),
) -> dict:
    require_permission(principal, "incident:read")
    session = SessionLocal()
    try:
        items = [incident_dump(session, row) for row in session.scalars(select(HealthIncidentRow))]
        items = [
            item
            for item in items
            if _matches(item, provider=provider, region=region, environment=environment, status=status, application=application)
        ]
        return _payload({"items": items, "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/health/incidents/{incident_id}")
def get_incident(incident_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "incident:read")
    session = SessionLocal()
    try:
        row = session.get(HealthIncidentRow, incident_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        return _payload(incident_dump(session, row))
    finally:
        session.close()


@router.post("/health/incidents/{incident_id}/acknowledge")
def ack_incident(incident_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "incident:acknowledge")
    session = SessionLocal()
    try:
        row = acknowledge_incident(session, incident_id, principal.user)
        if row is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        session.commit()
        return _payload(incident_dump(session, row))
    finally:
        session.close()


@router.post("/health/checks/{check_id}/run")
def run_check(check_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "health:run_check")
    session = SessionLocal()
    try:
        definition = session.get(HealthCheckDefinitionRow, check_id)
        kind = KIND_HTTP_HEALTH_CHECK
        if definition is None:
            raise HTTPException(status_code=404, detail="Health check not found")
        if definition.check_type in {"KUBERNETES_API", "NODE_READY", "DEPLOYMENT_AVAILABILITY", "POD_STATUS"}:
            kind = KIND_CLUSTER_HEALTH_SCAN
        elif definition.check_type in {"DATABASE_CONNECTIVITY", "REDIS_CONNECTIVITY", "RABBITMQ_CONNECTIVITY", "DEPENDENCY_HTTP"}:
            kind = KIND_DEPENDENCY_HEALTH_CHECK
        elif definition.check_type == "APPLICATION_AGGREGATE":
            kind = KIND_HEALTH_AGGREGATION
        record_audit(session, "HEALTH_CHECK_MANUALLY_TRIGGERED", actor=principal.user, object_name=check_id, detail=definition.check_type)
        session.commit()
    finally:
        session.close()
    job = enqueue_job(kind, target_id=check_id)
    payload = to_job_record(job).model_dump()
    payload["queued"] = True
    return _payload(payload)
