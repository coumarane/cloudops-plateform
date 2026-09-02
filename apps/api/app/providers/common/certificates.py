from __future__ import annotations

from app.core.config import settings

HEALTHY = "HEALTHY"
WARNING = "WARNING"
CRITICAL = "CRITICAL"
URGENT = "URGENT"
EXPIRED = "EXPIRED"
UNKNOWN = "UNKNOWN"

EXPIRY_STATUSES = (HEALTHY, WARNING, CRITICAL, URGENT, EXPIRED, UNKNOWN)

ALERT_KIND = {
    WARNING: "CERTIFICATE_WARNING",
    CRITICAL: "CERTIFICATE_CRITICAL",
    URGENT: "CERTIFICATE_URGENT",
    EXPIRED: "CERTIFICATE_EXPIRED",
}


def classify_expiry(days_remaining: int | None) -> str:
    """Operational expiry class. Backend source of truth — do not reimplement in the UI."""
    if days_remaining is None:
        return UNKNOWN
    if days_remaining <= 0:
        return EXPIRED
    if days_remaining <= 7:
        return URGENT
    if days_remaining <= 30:
        return CRITICAL
    if days_remaining <= 60:
        return WARNING
    return HEALTHY


def catalog_renewal_status(days_remaining: int | None, *, pending: bool = False) -> str:
    if pending:
        return "Renewing"
    status = classify_expiry(days_remaining)
    if status == EXPIRED:
        return "Expired"
    if status in {URGENT, CRITICAL, WARNING}:
        return "Expiring"
    return "OK"


def classify_certificate_age(days_remaining: int | None) -> tuple[str, str]:
    """Return (catalog renewalStatus, operational expiry class)."""
    return catalog_renewal_status(days_remaining), classify_expiry(days_remaining)


def alert_severity_for(status: str) -> str:
    mapping = {
        WARNING: settings.certificate_alert_severity_warning,
        CRITICAL: settings.certificate_alert_severity_critical,
        URGENT: settings.certificate_alert_severity_urgent,
        EXPIRED: settings.certificate_alert_severity_expired,
    }
    return mapping.get(status, "MEDIUM")


def catalog_alert_severity(internal: str) -> str:
    if internal in {"CRITICAL", "HIGH"}:
        return "critical"
    if internal in {"MEDIUM", "WARNING"}:
        return "warning"
    return "info"
