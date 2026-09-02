from __future__ import annotations

from app.core.logging import get_logger
from app.notifications.base import NotificationProvider

logger = get_logger(__name__)


class LogNotificationProvider(NotificationProvider):
    name = "log"

    def send(self, event_type: str, payload: dict[str, object]) -> None:
        logger.info(
            "certificate_notification event=%s domain=%s status=%s severity=%s",
            event_type,
            payload.get("domain"),
            payload.get("status"),
            payload.get("severity"),
        )


class EmailProvider(NotificationProvider):
    name = "email"

    def send(self, event_type: str, payload: dict[str, object]) -> None:
        logger.info("email provider not configured event=%s domain=%s", event_type, payload.get("domain"))


class TeamsProvider(NotificationProvider):
    name = "teams"

    def send(self, event_type: str, payload: dict[str, object]) -> None:
        logger.info("teams provider not configured event=%s domain=%s", event_type, payload.get("domain"))
