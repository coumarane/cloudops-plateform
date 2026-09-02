from __future__ import annotations


def classify_certificate_age(days_remaining: int | None) -> tuple[str, str]:
    """Return (API renewalStatus, operational class)."""
    if days_remaining is None:
        return "OK", "UNKNOWN"
    if days_remaining <= 0:
        return "Expired", "Expired"
    if days_remaining < 7:
        return "Expiring", "Urgent"
    if days_remaining <= 30:
        return "Expiring", "Critical"
    if days_remaining <= 60:
        return "Expiring", "Warning"
    return "OK", "Healthy"
