from __future__ import annotations

from app.notifications.webhook import SlackNotificationProvider

# Backwards-compatible alias. Alert modules must not import this.
SlackProvider = SlackNotificationProvider
