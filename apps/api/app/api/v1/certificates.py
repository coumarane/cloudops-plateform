from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.v1.listing import listed
from app.api.v1.params import parse_scope
from app.core.config import settings
from app.core.rbac import Principal, principal_from_headers, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.db.models import AcmCertificateRow, CertificateAlertRow, CertificateHistoryRow, CertificateValidationRow
from app.db.session import SessionLocal
from app.domain.models import Scope
from app.providers.common.certificates import CRITICAL, EXPIRED, HEALTHY, UNKNOWN, URGENT, WARNING
from app.services.catalog import catalog_service
from app.services.certificate_monitor import acknowledge_alert, history_payload, record_audit, validation_payload
from app.services.job_kinds import KIND_CERTIFICATE_DISCOVERY, KIND_CERTIFICATE_VALIDATE
from app.services.jobs import enqueue_job
from app.services.mappers import annotate_certificate, to_certificate_record, to_job_record

router = APIRouter()

STATUS_ALIASES = {
    "healthy": HEALTHY,
    "warning": WARNING,
    "critical": CRITICAL,
    "urgent": URGENT,
    "expired": EXPIRED,
    "unknown": UNKNOWN,
}

SORT_SEVERITY = {EXPIRED: 0, URGENT: 1, CRITICAL: 2, WARNING: 3, HEALTHY: 4, UNKNOWN: 5}


def _dump(payload) -> dict:
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload
    assert_no_secret_values(walk_strings(data))
    return data


def _filter_certificates(items, *, status: str | None, expires_within_days: int | None, sort: str | None):
    filtered = [annotate_certificate(item) for item in items]
    if status:
        wanted = STATUS_ALIASES.get(status.lower(), status.upper())
        filtered = [item for item in filtered if item.expiryStatus == wanted]
    if expires_within_days is not None:
        filtered = [
            item
            for item in filtered
            if item.daysRemaining is not None and 0 < item.daysRemaining <= expires_within_days
        ]
    key = (sort or "days_remaining").lower()
    if key in {"expiration", "expires_at", "expireson"}:
        filtered.sort(key=lambda item: item.expiresOn or "9999-12-31")
    elif key in {"environment"}:
        filtered.sort(key=lambda item: item.environment)
    elif key in {"severity", "status"}:
        filtered.sort(key=lambda item: SORT_SEVERITY.get(item.expiryStatus, 9))
    else:
        filtered.sort(key=lambda item: item.daysRemaining if item.daysRemaining is not None else 10_000)
    return filtered


def _alert_dump(row: CertificateAlertRow) -> dict:
    return {
        "id": row.id,
        "certificateId": row.certificate_id,
        "kind": row.kind,
        "severity": row.severity,
        "status": row.status,
        "domain": row.domain,
        "provider": row.provider,
        "region": row.region,
        "account": row.account,
        "environment": row.environment,
        "cluster": row.cluster,
        "expiresAt": row.expires_at.isoformat() if row.expires_at else None,
        "daysRemaining": row.days_remaining,
        "createdAt": row.created_at.isoformat(),
        "lastEvaluatedAt": row.last_evaluated_at.isoformat(),
        "acknowledgedAt": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def _resolve_row(session, certificate_id: str) -> AcmCertificateRow | None:
    row = session.get(AcmCertificateRow, certificate_id)
    if row is not None:
        return row
    if "-" in certificate_id:
        return session.get(AcmCertificateRow, certificate_id.rsplit("-", 1)[0])
    return None


@router.get("/certificates")
def list_certificates(
    scope: Scope = Depends(parse_scope),
    status: str | None = Query(default=None),
    expires_within_days: int | None = Query(default=None),
    sort: str | None = Query(default=None),
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "certificate:read")
    items = _filter_certificates(
        catalog_service.certificates(scope),
        status=status,
        expires_within_days=expires_within_days,
        sort=sort,
    )
    return listed(items)


@router.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "certificate:read")
    if certificate_id in {"scan", "secret"}:
        raise HTTPException(status_code=404, detail="Certificate not found")
    match = next((item for item in catalog_service.certificates(Scope()) if item.id == certificate_id), None)
    session = SessionLocal()
    try:
        row = _resolve_row(session, certificate_id)
        if match is None and row is None:
            raise HTTPException(status_code=404, detail="Certificate not found")
        record = match or annotate_certificate(to_certificate_record(row))
        payload = _dump(record)
        if row is not None:
            history = list(
                session.scalars(
                    select(CertificateHistoryRow)
                    .where(CertificateHistoryRow.certificate_id == row.id)
                    .order_by(CertificateHistoryRow.created_at.asc())
                )
            )
            alerts = list(
                session.scalars(
                    select(CertificateAlertRow)
                    .where(CertificateAlertRow.certificate_id == row.id)
                    .order_by(CertificateAlertRow.created_at.desc())
                )
            )
            validations = list(
                session.scalars(
                    select(CertificateValidationRow)
                    .where(CertificateValidationRow.certificate_id == row.id)
                    .order_by(CertificateValidationRow.checked_at.desc())
                )
            )
            payload["history"] = history_payload(history)
            payload["alerts"] = [_alert_dump(item) for item in alerts]
            payload["validations"] = validation_payload(validations)
        else:
            payload["history"] = []
            payload["alerts"] = []
            payload["validations"] = []
        return payload
    finally:
        session.close()


@router.get("/certificates/{certificate_id}/history")
def get_certificate_history(certificate_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "certificate:read")
    session = SessionLocal()
    try:
        rows = list(
            session.scalars(
                select(CertificateHistoryRow)
                .where(CertificateHistoryRow.certificate_id == certificate_id)
                .order_by(CertificateHistoryRow.created_at.asc())
            )
        )
        payload = {"items": history_payload(rows), "lastSynced": settings.last_synced}
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()


@router.get("/certificates/{certificate_id}/alerts")
def get_certificate_alerts(certificate_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "certificate:read")
    session = SessionLocal()
    try:
        rows = list(
            session.scalars(
                select(CertificateAlertRow)
                .where(CertificateAlertRow.certificate_id == certificate_id)
                .order_by(CertificateAlertRow.created_at.desc())
            )
        )
        payload = {"items": [_alert_dump(row) for row in rows], "lastSynced": settings.last_synced}
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()


@router.post("/certificates/scan")
def trigger_certificate_scan(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "certificate:scan")
    job = enqueue_job(KIND_CERTIFICATE_DISCOVERY)
    session = SessionLocal()
    try:
        record_audit(session, action="CERTIFICATE_SCAN_TRIGGERED", actor=principal.user, detail=f"job={job.id}")
        session.commit()
    finally:
        session.close()
    payload = to_job_record(job).model_dump()
    payload["queued"] = True
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.post("/certificates/{certificate_id}/validate")
def trigger_certificate_validate(certificate_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "certificate:validate")
    session = SessionLocal()
    try:
        row = _resolve_row(session, certificate_id)
        match = next((item for item in catalog_service.certificates(Scope()) if item.id == certificate_id), None)
        if row is None and match is None:
            raise HTTPException(status_code=404, detail="Certificate not found")
        job = enqueue_job(KIND_CERTIFICATE_VALIDATE, target_id=row.id if row is not None else certificate_id)
        record_audit(
            session,
            action="CERTIFICATE_VALIDATION_TRIGGERED",
            actor=principal.user,
            certificate_id=certificate_id,
            detail=f"job={job.id}",
        )
        session.commit()
    finally:
        session.close()
    payload = to_job_record(job).model_dump()
    payload["queued"] = True
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.post("/certificates/{certificate_id}/alerts/{alert_id}/acknowledge")
def acknowledge_certificate_alert(
    certificate_id: str,
    alert_id: str,
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "certificate:ack")
    session = SessionLocal()
    try:
        row = acknowledge_alert(session, alert_id, principal)
        if row is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        record_audit(
            session,
            action="CERTIFICATE_ALERT_ACKNOWLEDGED",
            actor=principal.user,
            certificate_id=certificate_id,
            detail=alert_id,
        )
        session.commit()
        payload = _alert_dump(row)
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()
