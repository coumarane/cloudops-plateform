from __future__ import annotations


class NotificationError(Exception):
    """Base notification error."""

    category = "PERMANENT_FAILURE"


class TemporaryNotificationError(NotificationError):
    category = "TEMPORARY_FAILURE"


class AuthNotificationError(NotificationError):
    category = "AUTH_FAILURE"


class ConfigurationNotificationError(NotificationError):
    category = "CONFIGURATION_FAILURE"


class RateLimitNotificationError(NotificationError):
    category = "RATE_LIMIT"


class PermanentNotificationError(NotificationError):
    category = "PERMANENT_FAILURE"
