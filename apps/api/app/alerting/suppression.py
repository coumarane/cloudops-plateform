from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting.models import AlertSignal
from app.db.models import AlertSuppressionRow, MaintenanceWindowRow
from app.db.repository import utcnow


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=utcnow().tzinfo)
    return value


def suppression_matches(row: AlertSuppressionRow, signal: AlertSignal, *, now: datetime | None = None) -> bool:
    if not row.enabled:
        return False
    current = _aware(now or utcnow())
    if _aware(row.starts_at) > current or _aware(row.ends_at) < current:
        return False
    if row.alert_type and row.alert_type.strip().upper() != (signal.alert_type or "").strip().upper():
        return False
    scope = (row.scope_type or "").lower()
    if scope in {"alert", "specific"}:
        return row.scope_id == (signal.source_id or "") or row.scope_id == (signal.correlation_id or "")
    if scope == "application":
        return row.scope_id == (signal.application_id or "")
    if scope == "environment":
        return row.scope_id in {(signal.environment_id or ""), (signal.environment or "")}
    if scope == "cluster":
        return row.scope_id == (signal.cluster_id or "")
    if scope == "alert_type":
        return True
    return False


def active_suppression(session: Session, signal: AlertSignal, *, now: datetime | None = None) -> AlertSuppressionRow | None:
    current = now or utcnow()
    rows = list(session.scalars(select(AlertSuppressionRow).where(AlertSuppressionRow.enabled.is_(True))))
    for row in rows:
        if suppression_matches(row, signal, now=current):
            return row
    return None


def maintenance_matches(row: MaintenanceWindowRow, signal: AlertSignal, *, now: datetime | None = None) -> bool:
    if not row.enabled:
        return False
    current = _aware(now or utcnow())
    if _aware(row.starts_at) > current or _aware(row.ends_at) < current:
        return False
    if row.provider and row.provider.lower() != (signal.provider or "").lower():
        return False
    if row.region and row.region.lower() != (signal.region or "").lower():
        return False
    if row.environment and row.environment.lower() != (signal.environment or "").lower():
        return False
    if row.application and row.application.lower() not in {(signal.application_id or "").lower(), ""}:
        return False
    return True


def active_maintenance(session: Session, signal: AlertSignal, *, now: datetime | None = None) -> MaintenanceWindowRow | None:
    current = now or utcnow()
    rows = list(session.scalars(select(MaintenanceWindowRow).where(MaintenanceWindowRow.enabled.is_(True))))
    for row in rows:
        if maintenance_matches(row, signal, now=current):
            return row
    return None


def expire_suppressions(session: Session, *, now: datetime | None = None) -> int:
    current = _aware(now or utcnow())
    changed = 0
    for row in session.scalars(select(AlertSuppressionRow).where(AlertSuppressionRow.enabled.is_(True))):
        if _aware(row.ends_at) < current:
            row.enabled = False
            changed += 1
    return changed


def expire_maintenance_windows(session: Session, *, now: datetime | None = None) -> int:
    current = _aware(now or utcnow())
    changed = 0
    for row in session.scalars(select(MaintenanceWindowRow).where(MaintenanceWindowRow.enabled.is_(True))):
        if _aware(row.ends_at) < current:
            row.enabled = False
            changed += 1
    return changed
