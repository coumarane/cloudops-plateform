from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.alerting.exceptions import AlertNotFoundError, AlertStateError
from app.alerting.models import AlertStatus, NotificationType
from app.alerting.presenters import (
    alert_dump,
    delivery_dump,
    destination_dump,
    event_dump,
    kpi_counts,
    policy_dump,
    related_context,
    route_dump,
    rule_dump,
    sort_alerts,
    window_dump,
)
from app.alerting.repositories import list_events, policy_steps
from app.alerting.service import (
    acknowledge_alert,
    ensure_defaults,
    record_audit,
    resolve_alert,
    suppress_alert,
)
from app.core.rbac import Principal, principal_from_headers, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.db.models import (
    AlertRow,
    AlertRuleRow,
    AlertRoutingRuleRow,
    MaintenanceWindowRow,
    NotificationDeliveryRow,
    NotificationDestinationRow,
    NotificationPolicyRow,
)
from app.db.repository import utcnow
from app.db.session import SessionLocal
from app.notifications.dispatcher import get_provider
from app.notifications.models import NotificationMessage
from app.secrets.factory import secret_backend

router = APIRouter()


def _payload(data: dict) -> dict:
    assert_no_secret_values(walk_strings(data))
    return data


def _parse_dt(value: str | None) -> datetime:
    if not value:
        raise HTTPException(status_code=400, detail="datetime is required")
    raw = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="invalid datetime") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class CommentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comment: str = Field(min_length=1, max_length=2000)


class SuppressBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=255)
    minutes: int = Field(default=60, ge=1, le=10080)
    scopeType: str = Field(default="alert", max_length=32)


class RuleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    alertType: str = Field(default="", max_length=64)
    enabled: bool = True
    providerFilter: str = Field(default="", max_length=32)
    regionFilter: str = Field(default="", max_length=32)
    environmentFilter: str = Field(default="", max_length=32)
    applicationFilter: str = Field(default="", max_length=128)
    severity: str = Field(default="MEDIUM", max_length=16)
    minimumOccurrences: int = Field(default=1, ge=1, le=1000)
    evaluationWindowSeconds: int = Field(default=0, ge=0, le=86400)
    notificationPolicyId: str = Field(default="", max_length=64)


class DestinationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    providerType: str = Field(min_length=1, max_length=32)
    description: str = Field(default="", max_length=255)
    enabled: bool = True
    configurationReference: str = Field(default="", max_length=256)
    secretValue: str | None = Field(default=None, max_length=65536)
    config: dict[str, object] = Field(default_factory=dict)


class WindowBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    scope: str = Field(default="", max_length=64)
    provider: str = Field(default="", max_length=32)
    region: str = Field(default="", max_length=32)
    environment: str = Field(default="", max_length=32)
    application: str = Field(default="", max_length=128)
    startsAt: str
    endsAt: str
    reason: str = Field(default="", max_length=255)
    changeTicket: str = Field(default="", max_length=64)


def _matches_alert(
    row: AlertRow,
    *,
    status: str | None,
    severity: str | None,
    provider: str | None,
    region: str | None,
    environment: str | None,
    application: str | None,
    alert_type: str | None,
) -> bool:
    if status and row.status.lower() != status.lower():
        return False
    if severity and row.severity.lower() != severity.lower():
        return False
    if provider and (row.provider or "").lower() != provider.lower():
        return False
    if region and (row.region or "").lower() != region.lower():
        return False
    if environment:
        env = (row.environment or "").lower()
        needle = environment.lower().replace("_", "-")
        if needle not in env.replace("/", "-") and needle not in env:
            return False
    if application:
        hay = f"{row.application_id} {row.title} {row.source_id}".lower()
        if application.lower() not in hay:
            return False
    if alert_type and row.alert_type.lower() != alert_type.lower():
        return False
    return True


def _safe_config(config: dict[str, object]) -> dict[str, object]:
    cleaned = dict(config)
    for key in list(cleaned):
        if key.lower() in {"url", "webhookurl", "token", "password", "smtp_password", "secret", "secretvalue"}:
            cleaned.pop(key)
    return cleaned


@router.get("/alerts")
def list_alerts(
    principal: Principal = Depends(principal_from_headers),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    region: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    application: str | None = Query(default=None),
    type: str | None = Query(default=None),
    order: str | None = Query(default="last_seen"),
) -> dict:
    require_permission(principal, "alert:read")
    session = SessionLocal()
    try:
        ensure_defaults(session)
        session.commit()
        rows = sort_alerts(list(session.scalars(select(AlertRow))), order)
        filtered = [
            row
            for row in rows
            if _matches_alert(
                row,
                status=status,
                severity=severity,
                provider=provider,
                region=region,
                environment=environment,
                application=application,
                alert_type=type,
            )
        ]
        items = [alert_dump(row) for row in filtered]
        return _payload({"items": items, "kpis": kpi_counts(rows), "lastSynced": utcnow().isoformat()})
    finally:
        session.close()


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert:read")
    session = SessionLocal()
    try:
        row = session.get(AlertRow, alert_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        payload = alert_dump(row)
        payload["related"] = related_context(session, row)
        payload["timeline"] = [event_dump(item) for item in list_events(session, row.id)]
        destinations = {item.id: item for item in session.scalars(select(NotificationDestinationRow))}
        payload["notifications"] = [
            delivery_dump(item, destinations.get(item.destination_id))
            for item in session.scalars(select(NotificationDeliveryRow).where(NotificationDeliveryRow.alert_id == row.id))
        ]
        return _payload(payload)
    finally:
        session.close()


@router.get("/alerts/{alert_id}/history")
def alert_history(alert_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert:read")
    session = SessionLocal()
    try:
        if session.get(AlertRow, alert_id) is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        return _payload({"items": [event_dump(item) for item in list_events(session, alert_id)]})
    finally:
        session.close()


@router.get("/alerts/{alert_id}/notifications")
def alert_notifications(alert_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert:read")
    session = SessionLocal()
    try:
        if session.get(AlertRow, alert_id) is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        destinations = {item.id: item for item in session.scalars(select(NotificationDestinationRow))}
        items = [
            delivery_dump(item, destinations.get(item.destination_id))
            for item in session.scalars(select(NotificationDeliveryRow).where(NotificationDeliveryRow.alert_id == alert_id))
        ]
        return _payload({"items": items})
    finally:
        session.close()


@router.post("/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: str, body: CommentBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert:acknowledge")
    session = SessionLocal()
    try:
        try:
            row = acknowledge_alert(session, alert_id, actor=principal.user, comment=body.comment)
        except AlertNotFoundError as error:
            raise HTTPException(status_code=404, detail="Alert not found") from error
        except AlertStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        session.commit()
        return _payload(alert_dump(row))
    finally:
        session.close()


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert_endpoint(alert_id: str, body: CommentBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert:resolve")
    session = SessionLocal()
    try:
        try:
            row = resolve_alert(session, alert_id, reason=body.comment, actor=principal.user, manual=True)
        except AlertNotFoundError as error:
            raise HTTPException(status_code=404, detail="Alert not found") from error
        session.commit()
        return _payload(alert_dump(row))
    finally:
        session.close()


@router.post("/alerts/{alert_id}/suppress")
def suppress_alert_endpoint(alert_id: str, body: SuppressBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert:suppress")
    session = SessionLocal()
    try:
        try:
            row = suppress_alert(session, alert_id, actor=principal.user, reason=body.reason, minutes=body.minutes)
        except AlertNotFoundError as error:
            raise HTTPException(status_code=404, detail="Alert not found") from error
        session.commit()
        return _payload(alert_dump(row))
    finally:
        session.close()


@router.get("/alert-rules")
def list_rules_endpoint(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert_rule:read")
    session = SessionLocal()
    try:
        ensure_defaults(session)
        session.commit()
        return _payload({"items": [rule_dump(row) for row in session.scalars(select(AlertRuleRow))]})
    finally:
        session.close()


@router.post("/alert-rules")
def create_rule(body: RuleBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert_rule:create")
    session = SessionLocal()
    try:
        now = utcnow()
        row = AlertRuleRow(
            id=str(uuid4()),
            name=body.name,
            alert_type=body.alertType,
            enabled=body.enabled,
            provider_filter=body.providerFilter,
            region_filter=body.regionFilter,
            environment_filter=body.environmentFilter,
            application_filter=body.applicationFilter,
            severity=body.severity.upper(),
            minimum_occurrences=body.minimumOccurrences,
            evaluation_window_seconds=body.evaluationWindowSeconds,
            notification_policy_id=body.notificationPolicyId,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        record_audit(session, "ALERT_RULE_CREATED", actor=principal.user, object_name=row.name)
        session.commit()
        return _payload(rule_dump(row))
    finally:
        session.close()


@router.put("/alert-rules/{rule_id}")
def update_rule(rule_id: str, body: RuleBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert_rule:update")
    session = SessionLocal()
    try:
        row = session.get(AlertRuleRow, rule_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        row.name = body.name
        row.alert_type = body.alertType
        row.enabled = body.enabled
        row.provider_filter = body.providerFilter
        row.region_filter = body.regionFilter
        row.environment_filter = body.environmentFilter
        row.application_filter = body.applicationFilter
        row.severity = body.severity.upper()
        row.minimum_occurrences = body.minimumOccurrences
        row.evaluation_window_seconds = body.evaluationWindowSeconds
        row.notification_policy_id = body.notificationPolicyId
        row.updated_at = utcnow()
        record_audit(session, "ALERT_RULE_UPDATED", actor=principal.user, object_name=row.name)
        session.commit()
        return _payload(rule_dump(row))
    finally:
        session.close()


@router.delete("/alert-rules/{rule_id}")
def delete_rule(rule_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "alert_rule:delete")
    session = SessionLocal()
    try:
        row = session.get(AlertRuleRow, rule_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        name = row.name
        session.delete(row)
        record_audit(session, "ALERT_RULE_DELETED", actor=principal.user, object_name=name)
        session.commit()
        return _payload({"deleted": True, "id": rule_id})
    finally:
        session.close()


@router.get("/notification-destinations")
def list_destinations(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "notification:read")
    session = SessionLocal()
    try:
        ensure_defaults(session)
        session.commit()
        return _payload({"items": [destination_dump(row) for row in session.scalars(select(NotificationDestinationRow))]})
    finally:
        session.close()


def _store_destination_secret(row: NotificationDestinationRow, secret_value: str | None) -> None:
    if not secret_value:
        return
    reference = row.configuration_reference or f"cloudops/notifications/{row.id}"
    secret_backend().store_secret(reference, secret_value)
    row.configuration_reference = reference


@router.post("/notification-destinations")
def create_destination(body: DestinationBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "notification:update")
    session = SessionLocal()
    try:
        now = utcnow()
        row = NotificationDestinationRow(
            id=str(uuid4()),
            name=body.name,
            provider_type=body.providerType.lower(),
            configuration_reference=body.configurationReference,
            config_json=json.dumps(_safe_config(body.config)),
            enabled=body.enabled,
            description=body.description,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        _store_destination_secret(row, body.secretValue)
        record_audit(session, "NOTIFICATION_DESTINATION_CREATED", actor=principal.user, object_name=row.name)
        session.commit()
        return _payload(destination_dump(row))
    finally:
        session.close()


@router.put("/notification-destinations/{destination_id}")
def update_destination(destination_id: str, body: DestinationBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "notification:update")
    session = SessionLocal()
    try:
        row = session.get(NotificationDestinationRow, destination_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Notification destination not found")
        row.name = body.name
        row.provider_type = body.providerType.lower()
        row.description = body.description
        row.enabled = body.enabled
        if body.configurationReference:
            row.configuration_reference = body.configurationReference
        row.config_json = json.dumps(_safe_config(body.config))
        row.updated_at = utcnow()
        _store_destination_secret(row, body.secretValue)
        record_audit(session, "NOTIFICATION_DESTINATION_UPDATED", actor=principal.user, object_name=row.name)
        session.commit()
        return _payload(destination_dump(row))
    finally:
        session.close()


@router.post("/notification-destinations/{destination_id}/test")
def test_destination(destination_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "notification:test")
    session = SessionLocal()
    try:
        row = session.get(NotificationDestinationRow, destination_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Notification destination not found")
        provider = get_provider(row.provider_type)
        config = json.loads(row.config_json or "{}") if row.config_json else {}
        secret = ""
        if row.configuration_reference:
            try:
                secret = secret_backend().get_secret(row.configuration_reference)
            except Exception:
                secret = ""
        message = NotificationMessage(
            event_type=NotificationType.TEST,
            title="CloudOps notification test",
            summary="Test notification from CloudOps Platform. Secret values are never included.",
            severity="INFO",
            payload={"destination": row.name},
            destination_id=row.id,
        )
        try:
            provider.validate_configuration(secret=secret, config=config if isinstance(config, dict) else {})
            external_id = provider.send(message, secret=secret, config=config if isinstance(config, dict) else {})
            status = "sent"
            detail = "test delivered"
        except Exception as error:
            external_id = ""
            status = "failed"
            detail = str(error)[:200]
        record_audit(session, "NOTIFICATION_TEST_SENT", actor=principal.user, object_name=row.name, detail=status)
        session.commit()
        return _payload({"id": row.id, "status": status, "externalMessageId": str(external_id or ""), "detail": detail})
    finally:
        session.close()


@router.get("/notification-policies")
def list_policies(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "notification:read")
    session = SessionLocal()
    try:
        ensure_defaults(session)
        session.commit()
        items = [policy_dump(row, policy_steps(session, row.id)) for row in session.scalars(select(NotificationPolicyRow))]
        return _payload({"items": items})
    finally:
        session.close()


@router.get("/alert-routing-rules")
def list_routes_endpoint(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "notification:read")
    session = SessionLocal()
    try:
        ensure_defaults(session)
        session.commit()
        return _payload({"items": [route_dump(row) for row in session.scalars(select(AlertRoutingRuleRow))]})
    finally:
        session.close()


@router.get("/maintenance-windows")
def list_windows(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "maintenance_window:read")
    session = SessionLocal()
    try:
        return _payload({"items": [window_dump(row) for row in session.scalars(select(MaintenanceWindowRow))]})
    finally:
        session.close()


@router.post("/maintenance-windows")
def create_window(body: WindowBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "maintenance_window:create")
    session = SessionLocal()
    try:
        starts = _parse_dt(body.startsAt)
        ends = _parse_dt(body.endsAt)
        if ends <= starts:
            raise HTTPException(status_code=400, detail="endsAt must be after startsAt")
        row = MaintenanceWindowRow(
            id=str(uuid4()),
            name=body.name,
            scope=body.scope,
            provider=body.provider,
            region=body.region,
            environment=body.environment,
            application=body.application,
            starts_at=starts,
            ends_at=ends,
            reason=body.reason,
            change_ticket=body.changeTicket,
            created_by=principal.user,
            enabled=True,
        )
        session.add(row)
        record_audit(session, "MAINTENANCE_WINDOW_CREATED", actor=principal.user, object_name=row.name, detail=body.reason)
        session.commit()
        return _payload(window_dump(row))
    finally:
        session.close()


@router.put("/maintenance-windows/{window_id}")
def update_window(window_id: str, body: WindowBody, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "maintenance_window:update")
    session = SessionLocal()
    try:
        row = session.get(MaintenanceWindowRow, window_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Maintenance window not found")
        row.name = body.name
        row.scope = body.scope
        row.provider = body.provider
        row.region = body.region
        row.environment = body.environment
        row.application = body.application
        row.starts_at = _parse_dt(body.startsAt)
        row.ends_at = _parse_dt(body.endsAt)
        row.reason = body.reason
        row.change_ticket = body.changeTicket
        record_audit(session, "MAINTENANCE_WINDOW_UPDATED", actor=principal.user, object_name=row.name)
        session.commit()
        return _payload(window_dump(row))
    finally:
        session.close()


@router.delete("/maintenance-windows/{window_id}")
def delete_window(window_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "maintenance_window:delete")
    session = SessionLocal()
    try:
        row = session.get(MaintenanceWindowRow, window_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Maintenance window not found")
        name = row.name
        session.delete(row)
        record_audit(session, "MAINTENANCE_WINDOW_DELETED", actor=principal.user, object_name=name)
        session.commit()
        return _payload({"deleted": True, "id": window_id})
    finally:
        session.close()
