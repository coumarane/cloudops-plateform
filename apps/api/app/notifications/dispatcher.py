from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting.models import AlertStatus, DeliveryStatus, FailureClass, NotificationType
from app.core.config import settings
from app.core.logging import get_logger, sanitize_text
from app.core.metrics import inc
from app.db.models import AlertEventRow, AlertRow, NotificationDeliveryRow, NotificationDestinationRow
from app.db.repository import utcnow
from app.notifications.base import NotificationProvider
from app.notifications.email import EmailNotificationProvider, LogNotificationProvider
from app.notifications.exceptions import NotificationError
from app.notifications.models import NotificationMessage
from app.notifications.webhook import SlackNotificationProvider, TeamsNotificationProvider, WebhookNotificationProvider
from app.secrets.factory import secret_backend

logger = get_logger(__name__)

TEST_PROVIDERS: dict[str, NotificationProvider] = {}

_PROVIDERS: dict[str, NotificationProvider] = {
    "log": LogNotificationProvider(),
    "email": EmailNotificationProvider(),
    "slack": SlackNotificationProvider(),
    "teams": TeamsNotificationProvider(),
    "webhook": WebhookNotificationProvider(),
}


def register_test_provider(name: str, provider: NotificationProvider | None) -> None:
    if provider is None:
        TEST_PROVIDERS.pop(name, None)
        return
    TEST_PROVIDERS[name] = provider


def get_provider(name: str) -> NotificationProvider:
    key = (name or "log").strip().lower()
    if key in TEST_PROVIDERS:
        return TEST_PROVIDERS[key]
    return _PROVIDERS.get(key) or _PROVIDERS["log"]


def retry_schedule() -> list[int]:
    raw = getattr(settings, "alert_notify_retry_seconds", "30,120,300")
    return [int(part.strip()) for part in str(raw).split(",") if part.strip()]


def _config(destination: NotificationDestinationRow) -> dict:
    import json

    try:
        payload = json.loads(destination.config_json or "{}")
    except Exception:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def _secret(destination: NotificationDestinationRow) -> str:
    if not destination.configuration_reference:
        return ""
    try:
        return secret_backend().get_secret(destination.configuration_reference)
    except Exception:
        return ""


def _message(alert: AlertRow, destination: NotificationDestinationRow, notification_type: str) -> NotificationMessage:
    import json

    try:
        extra = json.loads(alert.extra_json or "{}")
    except Exception:
        extra = {}
    return NotificationMessage(
        event_type=notification_type,
        title=alert.title,
        summary=alert.summary,
        severity=alert.severity,
        payload={
            "alertType": alert.alert_type,
            "provider": alert.provider,
            "region": alert.region,
            "environment": alert.environment,
            "applicationId": alert.application_id,
            "metadata": extra,
        },
        destination_id=destination.id,
        alert_id=alert.id,
    )


def _add_event(session: Session, alert_id: str, event_type: str, title: str, detail: str = "") -> None:
    session.add(
        AlertEventRow(
            id=str(uuid4()),
            alert_id=alert_id,
            event_type=event_type,
            title=title,
            detail=sanitize_text(detail)[:512],
            actor="system",
            created_at=utcnow(),
        )
    )


def classify_error(error: Exception) -> str:
    if isinstance(error, NotificationError):
        return error.category
    return FailureClass.TEMPORARY_FAILURE


def deliver(session: Session, delivery: NotificationDeliveryRow) -> NotificationDeliveryRow:
    alert = session.get(AlertRow, delivery.alert_id)
    destination = session.get(NotificationDestinationRow, delivery.destination_id)
    now = utcnow()
    delivery.attempt += 1
    if alert is None or destination is None or not destination.enabled:
        delivery.status = DeliveryStatus.FAILED
        delivery.failed_at = now
        delivery.error_category = FailureClass.CONFIGURATION_FAILURE
        return delivery
    if alert.status in {AlertStatus.RESOLVED, AlertStatus.SUPPRESSED} and delivery.notification_type != NotificationType.RECOVERY:
        delivery.status = DeliveryStatus.SKIPPED
        delivery.detail = "alert no longer notifiable"
        return delivery
    provider = get_provider(destination.provider_type)
    labels = {
        "severity": alert.severity.lower(),
        "provider": (alert.provider or "unknown").lower(),
        "environment_class": (alert.environment or "unknown").lower(),
        "notification_provider": provider.name,
    }
    secret = _secret(destination)
    config = _config(destination)
    try:
        provider.validate_configuration(secret=secret, config=config)
        external_id = provider.send(_message(alert, destination, delivery.notification_type), secret=secret, config=config)
        delivery.status = DeliveryStatus.SENT
        delivery.sent_at = now
        delivery.external_message_id = str(external_id or "")[:128]
        delivery.error_category = ""
        inc("cloudops_notifications_sent_total", labels)
        _add_event(session, alert.id, "notification", f"{provider.name} notification sent", delivery.notification_type)
        if delivery.notification_type == NotificationType.ESCALATION:
            inc("cloudops_alert_escalations_total", labels)
        if delivery.notification_type == NotificationType.RECOVERY:
            _add_event(session, alert.id, "recovery_notification", "recovery notification sent")
    except Exception as error:
        category = classify_error(error)
        delivery.error_category = category
        delivery.failed_at = now
        delivery.detail = sanitize_text(str(error))[:512]
        inc("cloudops_notifications_failed_total", {**labels, "notification_provider": provider.name})
        retries = retry_schedule()
        if category in {FailureClass.TEMPORARY_FAILURE, FailureClass.RATE_LIMIT} and delivery.attempt <= len(retries):
            delay = retries[min(delivery.attempt - 1, len(retries) - 1)]
            delivery.status = DeliveryStatus.RETRY
            delivery.next_retry_at = now + timedelta(seconds=delay)
        else:
            delivery.status = DeliveryStatus.FAILED
        logger.warning("Notification failed alert=%s dest=%s category=%s", alert.id, destination.id, category)
    return delivery


def dispatch_pending(session: Session, *, alert_id: str = "", limit: int = 50) -> int:
    now = utcnow()
    query = select(NotificationDeliveryRow).where(
        NotificationDeliveryRow.status.in_((DeliveryStatus.PENDING, DeliveryStatus.RETRY))
    )
    if alert_id:
        query = query.where(NotificationDeliveryRow.alert_id == alert_id)
    processed = 0
    for delivery in list(session.scalars(query.order_by(NotificationDeliveryRow.attempt.asc()))):
        if processed >= limit:
            break
        if delivery.next_retry_at is not None and delivery.next_retry_at > now:
            continue
        deliver(session, delivery)
        processed += 1
    return processed
