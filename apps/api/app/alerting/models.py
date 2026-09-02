from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class AlertStatus:
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SUPPRESSED = "SUPPRESSED"
    RESOLVED = "RESOLVED"


class AlertSeverity:
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DeliveryStatus:
    PENDING = "PENDING"
    SENT = "SENT"
    RETRY = "RETRY"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class NotificationType:
    INITIAL = "initial"
    REPEAT = "repeat"
    ESCALATION = "escalation"
    RECOVERY = "recovery"
    TEST = "test"


class FailureClass:
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    AUTH_FAILURE = "AUTH_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"


ACTIVE_STATUSES = (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.SUPPRESSED)

SEVERITY_RANK = {
    AlertSeverity.INFO: 0,
    AlertSeverity.LOW: 1,
    AlertSeverity.MEDIUM: 2,
    AlertSeverity.HIGH: 3,
    AlertSeverity.CRITICAL: 4,
}


def normalize_severity(value: str) -> str:
    raw = (value or "").strip().upper()
    mapping = {
        "INFO": AlertSeverity.INFO,
        "LOW": AlertSeverity.LOW,
        "MEDIUM": AlertSeverity.MEDIUM,
        "HIGH": AlertSeverity.HIGH,
        "CRITICAL": AlertSeverity.CRITICAL,
        "WARNING": AlertSeverity.MEDIUM,
        "WARN": AlertSeverity.MEDIUM,
    }
    return mapping.get(raw, AlertSeverity.MEDIUM)


def ui_severity(value: str) -> str:
    rank = SEVERITY_RANK.get(normalize_severity(value), 2)
    if rank >= 3:
        return "critical"
    if rank >= 2:
        return "warning"
    return "info"


@dataclass
class AlertSignal:
    alert_type: str
    source_type: str
    source_id: str
    title: str
    summary: str = ""
    severity: str = AlertSeverity.HIGH
    provider: str = ""
    region: str = ""
    account_id: str = ""
    environment_id: str = ""
    environment: str = ""
    application_id: str = ""
    cluster_id: str = ""
    correlation_id: str = ""
    metadata: dict = field(default_factory=dict)
    recovered: bool = False
    resolution_reason: str = ""
    first_seen_at: datetime | None = None
