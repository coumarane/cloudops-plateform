from __future__ import annotations

from app.notifications.dispatcher import get_provider
from app.notifications.models import NotificationMessage


def get_notification_provider():
    """Deprecated compatibility wrapper. New code must use alerting.service.publish()."""
    return get_provider("log")
