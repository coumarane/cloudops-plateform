from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.correlation import current_correlation_id
from app.core.logging import get_logger, sanitize_text
from app.core.metrics import inc, observe_duration, set_gauge
from app.core.rbac import Principal
from app.db.models import (
    AcmCertificateRow,
    CertificateAlertRow,
    CertificateAuditRow,
    CertificateEndpointRow,
    CertificateHistoryRow,
    CertificateValidationRow,
    NotificationEventRow,
)
from app.db.repository import certificate_public_id, utcnow
from app.db.session import SessionLocal
from app.notifications.factory import get_notification_provider
from app.providers.common.certificates import (
    ALERT_KIND,
    CRITICAL,
    EXPIRED,
    HEALTHY,
    UNKNOWN,
    URGENT,
    WARNING,
    alert_severity_for,
    catalog_alert_severity,
    classify_expiry,
)
from app.providers.common.models import DiscoveredCertificate
from app.services.endpoint_tls import EndpointPolicyError, check_https_endpoint
from app.services.mappers import _age

logger = get_logger(__name__)

HISTORY_FIRST = "first_discovered"
HISTORY_EXPIRY = "expiration_changed"
HISTORY_ISSUER = "issuer_changed"
HISTORY_SERIAL = "serial_changed"
HISTORY_RENEWED = "renewed"
HISTORY_DISAPPEARED = "disappeared"
HISTORY_REDISCOVERED = "rediscovered"

STATUS_RANK = {
    HEALTHY: 0,
    UNKNOWN: 0,
    WARNING: 1,
    CRITICAL: 2,
    URGENT: 3,
    EXPIRED: 4,
}

SEVERITY_SORT = {EXPIRED: 0, URGENT: 1, CRITICAL: 2, WARNING: 3, HEALTHY: 4, UNKNOWN: 5}


def _days_from(not_after: datetime | None, now: datetime) -> int | None:
    if not_after is None:
        return None
    moment = not_after if not_after.tzinfo else not_after.replace(tzinfo=timezone.utc)
    return (moment - now).days


def _history(session: Session, certificate_id: str, event: str, detail: str = "") -> None:
    session.add(
        CertificateHistoryRow(
            id=str(uuid4()),
            certificate_id=certificate_id,
            event=event,
            detail=sanitize_text(detail),
            created_at=utcnow(),
        )
    )


def record_audit(
    session: Session,
    *,
    action: str,
    actor: str,
    certificate_id: str = "",
    provider: str = "",
    region: str = "",
    environment: str = "",
    detail: str = "",
) -> None:
    session.add(
        CertificateAuditRow(
            id=str(uuid4()),
            action=action,
            certificate_id=certificate_id,
            actor=actor,
            provider=provider,
            platform_region=region,
            environment=environment,
            result="succeeded",
            detail=sanitize_text(detail),
            correlation_id=current_correlation_id(),
            created_at=utcnow(),
        )
    )


def upsert_discovered(session: Session, item: DiscoveredCertificate, *, now: datetime | None = None) -> AcmCertificateRow:
    now = now or utcnow()
    public_id = certificate_public_id(item.arn)
    row = session.get(AcmCertificateRow, public_id)
    days = item.days_remaining if item.days_remaining is not None else _days_from(item.not_after, now)
    if item.not_after is not None:
        days = _days_from(item.not_after, now)
    status = classify_expiry(days)
    auto_renew = item.auto_renew or "PENDING" in (item.renewal_eligibility or "").upper() or (
        item.renewal_eligibility or ""
    ).upper() in {"ELIGIBLE", "PENDING_AUTO_RENEWAL"}
    created = row is None
    rediscovered = row is not None and not row.present
    previous_expiry = row.not_after if row else None
    previous_issuer = row.issuer if row else None
    previous_serial = row.serial_number if row else None
    previous_status = row.expiry_status if row else None
    if row is None:
        row = AcmCertificateRow(id=public_id, arn=item.arn, domain_name=item.domain_name, last_checked=now)
        session.add(row)
        row.first_seen_at = now
    row.arn = item.arn
    row.domain_name = item.domain_name
    row.subject_alternative_names = json.dumps(item.subject_alternative_names)
    row.issuer = item.issuer
    row.status = item.status or status
    row.not_before = item.not_before
    row.not_after = item.not_after
    row.days_remaining = days
    row.in_use_by = json.dumps(item.in_use_by)
    row.renewal_eligibility = item.renewal_eligibility
    row.last_checked = item.last_checked or now
    row.provider = item.provider or "AWS"
    row.platform_region = item.platform_region
    row.environment = item.environment
    row.account_alias = item.account_alias
    row.cloud_region = item.cloud_region
    row.present = True
    row.cluster_name = item.cluster_name
    row.namespace = item.namespace
    row.source = item.source or ("acm" if item.provider == "AWS" else "cas")
    row.serial_number = item.serial_number or (row.serial_number or "")
    row.auto_renew = auto_renew
    row.discovery_status = "ok"
    row.last_seen_at = now
    row.cluster_id = item.cluster_id or row.cluster_id
    row.application_id = item.application_id or row.application_id
    row.expiry_status = status
    row.hostname = item.hostname or row.hostname or item.domain_name
    row.last_error = ""
    row.last_error_class = ""
    row.last_attempted_at = now
    if created:
        _history(session, row.id, HISTORY_FIRST, f"Discovered {row.domain_name} from {row.source}")
    elif rediscovered:
        _history(session, row.id, HISTORY_REDISCOVERED, f"Rediscovered {row.domain_name}")
    else:
        if previous_expiry != item.not_after:
            _history(session, row.id, HISTORY_EXPIRY, "Expiration date changed")
            if previous_status in {EXPIRED, URGENT, CRITICAL, WARNING} and status == HEALTHY:
                _history(session, row.id, HISTORY_RENEWED, "Certificate renewed")
            elif previous_status == EXPIRED and status != EXPIRED:
                _history(session, row.id, HISTORY_RENEWED, "Certificate renewed")
        if previous_issuer is not None and previous_issuer != item.issuer:
            _history(session, row.id, HISTORY_ISSUER, "Issuer changed")
        if previous_serial and item.serial_number and previous_serial != item.serial_number:
            _history(session, row.id, HISTORY_SERIAL, "Serial number changed")
            if status == HEALTHY and previous_status != HEALTHY:
                _history(session, row.id, HISTORY_RENEWED, "Certificate renewed")
    session.flush()
    return row


def mark_missing(session: Session, account_alias: str, seen_ids: set[str], *, source: str | None = None) -> None:
    query = select(AcmCertificateRow).where(AcmCertificateRow.account_alias == account_alias)
    if source:
        query = query.where(AcmCertificateRow.source == source)
    for row in session.scalars(query).all():
        if row.id in seen_ids:
            continue
        if row.source in {"https"}:
            continue
        if row.present:
            row.present = False
            _history(session, row.id, HISTORY_DISAPPEARED, "Disappeared from source")


def refresh_days(session: Session, *, now: datetime | None = None) -> int:
    now = now or utcnow()
    changed = 0
    for row in session.scalars(select(AcmCertificateRow)).all():
        days = _days_from(row.not_after, now)
        status = classify_expiry(days)
        if row.days_remaining != days or row.expiry_status != status:
            changed += 1
        row.days_remaining = days
        row.expiry_status = status
        row.last_checked = now
    return changed


def _active_alert(session: Session, certificate_id: str) -> CertificateAlertRow | None:
    return session.scalar(
        select(CertificateAlertRow).where(
            CertificateAlertRow.certificate_id == certificate_id,
            CertificateAlertRow.status.in_(("OPEN", "ACKNOWLEDGED")),
        )
    )


def _notify(session: Session, certificate_id: str, event_type: str, payload: dict[str, object]) -> None:
    cooldown = timedelta(seconds=settings.certificate_notification_cooldown_seconds)
    cutoff = utcnow() - cooldown
    recent = session.scalar(
        select(NotificationEventRow).where(
            NotificationEventRow.certificate_id == certificate_id,
            NotificationEventRow.event_type == event_type,
            NotificationEventRow.created_at >= cutoff,
        )
    )
    if recent is not None:
        return
    provider = get_notification_provider()
    provider.send(event_type, payload)
    session.add(
        NotificationEventRow(
            id=str(uuid4()),
            certificate_id=certificate_id,
            event_type=event_type,
            channel=provider.name,
            payload=sanitize_text(json.dumps(payload, default=str)),
            created_at=utcnow(),
        )
    )


def evaluate_alerts(session: Session, *, now: datetime | None = None) -> dict[str, int]:
    now = now or utcnow()
    created = updated = resolved = 0
    for row in session.scalars(select(AcmCertificateRow)).all():
        status = row.expiry_status or classify_expiry(row.days_remaining)
        row.expiry_status = status
        alert = _active_alert(session, row.id)
        payload = {
            "certificate_id": row.id,
            "domain": row.domain_name,
            "provider": row.provider,
            "region": row.platform_region,
            "account": row.account_alias,
            "environment": row.environment,
            "cluster": row.cluster_name,
            "expires_at": row.not_after.isoformat() if row.not_after else None,
            "days_remaining": row.days_remaining,
            "status": status,
            "severity": alert_severity_for(status),
        }
        if status in ALERT_KIND:
            kind = ALERT_KIND[status]
            severity = alert_severity_for(status)
            if alert is None:
                alert = CertificateAlertRow(
                    id=str(uuid4()),
                    certificate_id=row.id,
                    kind=kind,
                    severity=severity,
                    status="OPEN",
                    domain=row.domain_name,
                    provider=row.provider,
                    region=row.platform_region,
                    account=row.account_alias,
                    environment=row.environment or "DEV",
                    cluster=row.cluster_name,
                    application=row.application_id,
                    expires_at=row.not_after,
                    days_remaining=row.days_remaining,
                    created_at=now,
                    last_evaluated_at=now,
                )
                session.add(alert)
                created += 1
                _notify(session, row.id, kind, payload)
            else:
                alert.last_evaluated_at = now
                alert.expires_at = row.not_after
                alert.days_remaining = row.days_remaining
                alert.domain = row.domain_name
                previous_rank = STATUS_RANK.get(alert.kind.replace("CERTIFICATE_", ""), 0)
                if alert.kind != kind:
                    alert.kind = kind
                    alert.severity = severity
                    updated += 1
                    if STATUS_RANK.get(status, 0) >= previous_rank:
                        _notify(session, row.id, kind, payload)
                else:
                    alert.severity = severity
        elif alert is not None:
            alert.status = "RESOLVED"
            alert.resolved_at = now
            alert.last_evaluated_at = now
            resolved += 1
            _notify(session, row.id, "CERTIFICATE_RECOVERED", {**payload, "status": status})
    session.flush()
    refresh_certificate_gauges(session)
    logger.info("Certificate alerts created=%s updated=%s resolved=%s", created, updated, resolved)
    return {"created": created, "updated": updated, "resolved": resolved}


def acknowledge_alert(session: Session, alert_id: str, principal: Principal) -> CertificateAlertRow | None:
    row = session.get(CertificateAlertRow, alert_id)
    if row is None or row.status == "RESOLVED":
        return row
    row.status = "ACKNOWLEDGED"
    row.acknowledged_at = utcnow()
    row.acknowledged_by = principal.user
    row.last_evaluated_at = utcnow()
    return row


def refresh_certificate_gauges(session: Session) -> None:
    counts: dict[tuple[str, str, str, str], int] = {}
    for row in session.scalars(select(AcmCertificateRow).where(AcmCertificateRow.present.is_(True))).all():
        status = row.expiry_status or classify_expiry(row.days_remaining)
        key = (row.provider or "AWS", row.platform_region or "", row.environment or "", status)
        counts[key] = counts.get(key, 0) + 1
    seen_total: set[tuple[str, str, str]] = set()
    for (provider, region, environment, status), value in counts.items():
        labels = {
            "provider": provider.lower(),
            "region": region.lower(),
            "environment": environment.lower() or "unknown",
            "status": status,
        }
        set_gauge("cloudops_certificates_total", labels, value)
        scope = (provider, region, environment)
        seen_total.add(scope)
    expiring: dict[tuple[str, str, str], int] = {}
    expired: dict[tuple[str, str, str], int] = {}
    for (provider, region, environment, status), value in counts.items():
        scope = (provider, region, environment)
        if status in {WARNING, CRITICAL, URGENT}:
            expiring[scope] = expiring.get(scope, 0) + value
        if status == EXPIRED:
            expired[scope] = expired.get(scope, 0) + value
    for provider, region, environment in seen_total:
        labels = {
            "provider": provider.lower(),
            "region": region.lower(),
            "environment": environment.lower() or "unknown",
        }
        set_gauge("cloudops_certificates_expiring_total", labels, expiring.get((provider, region, environment), 0))
        set_gauge("cloudops_certificates_expired_total", labels, expired.get((provider, region, environment), 0))


def refresh_monitoring(session: Session) -> dict[str, int]:
    refresh_days(session)
    return evaluate_alerts(session)


def to_operational_alert(row: CertificateAlertRow):
    from app.domain.models import OperationalAlert
    from app.data.hrefs import catalog_href

    title = {
        "CERTIFICATE_WARNING": "Certificate warning",
        "CERTIFICATE_CRITICAL": "Certificate critical",
        "CERTIFICATE_URGENT": "Certificate urgent",
        "CERTIFICATE_EXPIRED": "Certificate expired",
    }.get(row.kind, row.kind.replace("_", " ").title())
    environment = row.environment or "DEV"
    region = row.region or "EMEA"
    provider = row.provider or "AWS"
    href = catalog_href(
        "/certificates",
        provider,  # type: ignore[arg-type]
        region,  # type: ignore[arg-type]
        environment,  # type: ignore[arg-type]
        selected=row.certificate_id,
    )
    return OperationalAlert(
        id=row.id,
        severity=catalog_alert_severity(row.severity),  # type: ignore[arg-type]
        title=title,
        objectName=row.domain,
        provider=provider,  # type: ignore[arg-type]
        region=region,  # type: ignore[arg-type]
        environment=environment,  # type: ignore[arg-type]
        age=_age(row.created_at),
        href=href,
    )


def history_payload(rows: list[CertificateHistoryRow]) -> list[dict[str, str]]:
    return [
        {"id": row.id, "event": row.event, "detail": row.detail, "createdAt": row.created_at.isoformat()}
        for row in rows
    ]


def validation_payload(rows: list[CertificateValidationRow]) -> list[dict[str, object]]:
    return [
        {
            "id": row.id,
            "hostname": row.hostname,
            "handshakeOk": row.handshake_ok,
            "latencyMs": row.latency_ms,
            "issuer": row.issuer,
            "expiresAt": row.expires_at.isoformat() if row.expires_at else None,
            "error": row.error,
            "checkedAt": row.checked_at.isoformat(),
        }
        for row in rows
    ]


def record_validation(
    session: Session,
    certificate: AcmCertificateRow,
    *,
    hostname: str,
    handshake_ok: bool,
    latency_ms: int,
    issuer: str = "",
    expires_at: datetime | None = None,
    error: str = "",
) -> CertificateValidationRow:
    row = CertificateValidationRow(
        id=str(uuid4()),
        certificate_id=certificate.id,
        hostname=hostname,
        handshake_ok=handshake_ok,
        latency_ms=latency_ms,
        issuer=issuer,
        expires_at=expires_at,
        error=sanitize_text(error),
        checked_at=utcnow(),
    )
    session.add(row)
    certificate.handshake_ok = handshake_ok
    certificate.handshake_latency_ms = latency_ms
    certificate.last_checked = utcnow()
    certificate.last_attempted_at = utcnow()
    if error:
        certificate.last_error = sanitize_text(error)
        certificate.last_error_class = "EndpointCheck"
    else:
        certificate.last_error = ""
        certificate.last_error_class = ""
    if expires_at:
        certificate.not_after = expires_at
        certificate.days_remaining = _days_from(expires_at, utcnow())
        certificate.expiry_status = classify_expiry(certificate.days_remaining)
    if issuer:
        certificate.issuer = issuer
    return row


def upsert_https_result(
    session: Session,
    endpoint: CertificateEndpointRow,
    result,
) -> AcmCertificateRow:
    now = utcnow()
    host = endpoint.hostname
    parsed = result.certificate
    item = DiscoveredCertificate(
        arn=f"cloudops:https:{host}",
        domain_name=parsed.common_name if parsed and parsed.common_name else host,
        subject_alternative_names=list(parsed.subject_alternative_names) if parsed else [host],
        issuer=parsed.issuer if parsed else "",
        status="ISSUED" if result.success else "UNKNOWN",
        not_before=parsed.valid_from if parsed else None,
        not_after=parsed.expires_at if parsed else None,
        days_remaining=parsed.days_remaining if parsed else None,
        in_use_by=[endpoint.url],
        renewal_eligibility="UNKNOWN",
        last_checked=now,
        environment=endpoint.environment or "DEV",
        platform_region=endpoint.region or "EMEA",
        account_alias=endpoint.account_alias or "https",
        cloud_region=endpoint.region or "",
        provider=endpoint.provider or "AWS",
        source="https",
        serial_number=parsed.serial_number if parsed else "",
        hostname=host,
    )
    row = upsert_discovered(session, item, now=now)
    row.handshake_ok = result.success
    row.handshake_latency_ms = result.latency_ms
    row.last_error = "" if result.success else result.error_category
    row.last_error_class = "" if result.success else result.error_category
    record_validation(
        session,
        row,
        hostname=host,
        handshake_ok=result.success,
        latency_ms=result.latency_ms,
        issuer=item.issuer,
        expires_at=item.not_after,
        error="" if result.success else result.error_category,
    )
    return row


def enabled_endpoints(session: Session) -> list[CertificateEndpointRow]:
    return list(session.scalars(select(CertificateEndpointRow).where(CertificateEndpointRow.enabled.is_(True))))


def run_expiry_scan(job_id: str) -> int:
    from app.db.repository import InventoryRepository

    started = utcnow()
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        repo.mark_job_running(job_id)
        changed = refresh_days(session)
        evaluate_alerts(session)
        repo.mark_job_finished(job_id, status="succeeded", detail=f"expiry-scan: {changed} certificates updated")
        session.commit()
        observe_duration(
            "cloudops_certificate_scan_duration_seconds",
            {"job": "expiry"},
            (utcnow() - started).total_seconds(),
        )
        return changed
    except Exception as error:
        session.rollback()
        inc("cloudops_certificate_scan_failures_total", {"job": "expiry"})
        finish = SessionLocal()
        try:
            InventoryRepository(finish).mark_job_finished(
                job_id, status="failed", detail=sanitize_text(str(error)), error_class=error.__class__.__name__
            )
            finish.commit()
        finally:
            finish.close()
        raise
    finally:
        session.close()


def run_alert_evaluation(job_id: str) -> int:
    from app.db.repository import InventoryRepository

    started = utcnow()
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        repo.mark_job_running(job_id)
        stats = evaluate_alerts(session)
        repo.mark_job_finished(job_id, status="succeeded", detail=f"alert-evaluation: {stats}")
        session.commit()
        observe_duration(
            "cloudops_certificate_scan_duration_seconds",
            {"job": "alerts"},
            (utcnow() - started).total_seconds(),
        )
        return stats["created"] + stats["updated"] + stats["resolved"]
    except Exception as error:
        session.rollback()
        inc("cloudops_certificate_scan_failures_total", {"job": "alerts"})
        finish = SessionLocal()
        try:
            InventoryRepository(finish).mark_job_finished(
                job_id, status="failed", detail=sanitize_text(str(error)), error_class=error.__class__.__name__
            )
            finish.commit()
        finally:
            finish.close()
        raise
    finally:
        session.close()


def run_endpoint_validation(job_id: str) -> int:
    from app.db.repository import InventoryRepository

    started = utcnow()
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        repo.mark_job_running(job_id)
        checked = 0
        for endpoint in enabled_endpoints(session):
            try:
                result = check_https_endpoint(endpoint.url, registered=True)
                upsert_https_result(session, endpoint, result)
                checked += 1
            except EndpointPolicyError as error:
                logger.warning("Skipping HTTPS endpoint url=%s error=%s", endpoint.hostname, error)
                inc(
                    "cloudops_certificate_scan_failures_total",
                    {"provider": (endpoint.provider or "aws").lower(), "job": "endpoint"},
                )
            except Exception as error:
                logger.warning("HTTPS endpoint check failed host=%s", endpoint.hostname)
                inc(
                    "cloudops_certificate_scan_failures_total",
                    {"provider": (endpoint.provider or "aws").lower(), "job": "endpoint"},
                )
                endpoint_row = session.get(CertificateEndpointRow, endpoint.id)
                if endpoint_row:
                    pass
                _ = error
        evaluate_alerts(session)
        repo.mark_job_finished(job_id, status="succeeded", detail=f"endpoint-validation: {checked} endpoints")
        session.commit()
        observe_duration(
            "cloudops_certificate_scan_duration_seconds",
            {"job": "endpoint"},
            (utcnow() - started).total_seconds(),
        )
        return checked
    except Exception as error:
        session.rollback()
        inc("cloudops_certificate_scan_failures_total", {"job": "endpoint"})
        finish = SessionLocal()
        try:
            InventoryRepository(finish).mark_job_finished(
                job_id, status="failed", detail=sanitize_text(str(error)), error_class=error.__class__.__name__
            )
            finish.commit()
        finally:
            finish.close()
        raise
    finally:
        session.close()


def run_certificate_validate(job_id: str) -> int:
    from app.db.repository import InventoryRepository

    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        job = repo.mark_job_running(job_id)
        if job is None:
            return 0
        cert = session.get(AcmCertificateRow, job.target_id)
        if cert is None:
            repo.mark_job_finished(job_id, status="failed", detail="Certificate not found", error_class="NotFound")
            session.commit()
            return 0
        host = cert.hostname or cert.domain_name
        url = host if host.startswith("https://") else f"https://{host.lstrip('*.')}"
        try:
            result = check_https_endpoint(url, registered=True)
            record_validation(
                session,
                cert,
                hostname=result.hostname,
                handshake_ok=result.success,
                latency_ms=result.latency_ms,
                issuer=result.certificate.issuer if result.certificate else "",
                expires_at=result.certificate.expires_at if result.certificate else None,
                error="" if result.success else result.error_category,
            )
            if result.certificate and result.certificate.expires_at:
                cert.not_after = result.certificate.expires_at
                cert.not_before = result.certificate.valid_from
                cert.days_remaining = result.certificate.days_remaining
                cert.expiry_status = classify_expiry(cert.days_remaining)
                if result.certificate.issuer:
                    cert.issuer = result.certificate.issuer
                if result.certificate.serial_number:
                    cert.serial_number = result.certificate.serial_number
            evaluate_alerts(session)
            repo.mark_job_finished(job_id, status="succeeded", detail=f"validated {result.hostname}")
        except EndpointPolicyError as error:
            record_validation(
                session,
                cert,
                hostname=host,
                handshake_ok=False,
                latency_ms=0,
                error=str(error),
            )
            repo.mark_job_finished(job_id, status="succeeded", detail=sanitize_text(str(error)))
        session.commit()
        return 1
    except Exception as error:
        session.rollback()
        finish = SessionLocal()
        try:
            InventoryRepository(finish).mark_job_finished(
                job_id, status="failed", detail=sanitize_text(str(error)), error_class=error.__class__.__name__
            )
            finish.commit()
        finally:
            finish.close()
        raise
    finally:
        session.close()
