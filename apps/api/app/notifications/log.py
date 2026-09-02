from __future__ import annotations

from app.core.logging import get_logger
from app.notifications.base import NotificationProvider
from app.notifications.email import EmailNotificationProvider, LogNotificationProvider
from app.notifications.models import NotificationMessage

logger = get_logger(__name__)

LogProvider = LogNotificationProvider
EmailProvider = EmailNotificationProvider
