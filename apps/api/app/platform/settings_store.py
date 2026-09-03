from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import PlatformSettingRow
from app.db.repository import utcnow

DEFAULTS: dict[str, str] = {
    "discovery_interval_seconds": "3600",
    "certificate_threshold_warning_days": "30",
    "certificate_threshold_critical_days": "14",
    "health_scan_interval_seconds": str(settings.health_cluster_interval_seconds),
    "health_result_retention_days": str(settings.health_result_retention_days),
    "pipeline_run_retention_days": str(settings.pipeline_run_retention_days),
    "alert_prd_default_severity": "CRITICAL",
    "alert_dev_default_severity": "INFO",
}

SETTING_LABELS = {
    "discovery_interval_seconds": "Discovery schedule (seconds)",
    "certificate_threshold_warning_days": "Certificate warning threshold (days)",
    "certificate_threshold_critical_days": "Certificate critical threshold (days)",
    "health_scan_interval_seconds": "Health scan interval (seconds)",
    "health_result_retention_days": "Health result retention (days)",
    "pipeline_run_retention_days": "Pipeline run retention (days)",
    "alert_prd_default_severity": "PRD default alert severity",
    "alert_dev_default_severity": "DEV default alert severity",
}


def list_settings(session: Session) -> list[dict]:
    rows = {row.key: row for row in session.query(PlatformSettingRow)}
    items = []
    now = utcnow()
    for key, default in DEFAULTS.items():
        row = rows.get(key)
        items.append(
            {
                "key": key,
                "label": SETTING_LABELS[key],
                "value": row.value if row is not None else default,
                "updatedAt": (row.updated_at if row is not None else now).isoformat(),
                "updatedBy": row.updated_by if row is not None else "system",
            }
        )
    return items


def update_settings(session: Session, values: dict[str, str], actor: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    for key, value in values.items():
        if key not in DEFAULTS:
            continue
        row = session.get(PlatformSettingRow, key)
        if row is None:
            row = PlatformSettingRow(key=key, value=str(value), updated_at=now, updated_by=actor)
            session.add(row)
        else:
            row.value = str(value)
            row.updated_at = now
            row.updated_by = actor
    session.flush()
    return list_settings(session)
