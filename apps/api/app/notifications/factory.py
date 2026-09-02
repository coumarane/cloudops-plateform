from __future__ import annotations

from app.core.config import settings
from app.notifications.base import NotificationProvider
from app.notifications.log import EmailProvider, LogNotificationProvider, TeamsProvider
from app.notifications.slack import SlackProvider


def get_notification_provider() -> NotificationProvider:
    name = (settings.certificate_notification_provider or "log").strip().lower()
    if name == "slack":
        return SlackProvider()
    if name == "email":
        return EmailProvider()
    if name == "teams":
        return TeamsProvider()
    return LogNotificationProvider()
