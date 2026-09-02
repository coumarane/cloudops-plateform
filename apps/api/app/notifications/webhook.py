from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.core.logging import get_logger
from app.notifications.base import NotificationProvider
from app.notifications.exceptions import (
    AuthNotificationError,
    ConfigurationNotificationError,
    PermanentNotificationError,
    RateLimitNotificationError,
    TemporaryNotificationError,
)
from app.notifications.models import NotificationMessage

logger = get_logger(__name__)


def _post(url: str, body: dict, timeout: float = 8) -> str:
    if not url:
        raise ConfigurationNotificationError("Webhook URL is missing")
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            return f"http-{response.status}"
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise AuthNotificationError(str(error)) from error
        if error.code == 429:
            raise RateLimitNotificationError(str(error)) from error
        if error.code >= 500:
            raise TemporaryNotificationError(str(error)) from error
        raise PermanentNotificationError(str(error)) from error
    except TimeoutError as error:
        raise TemporaryNotificationError("webhook timeout") from error
    except OSError as error:
        raise TemporaryNotificationError(str(error)) from error


class WebhookNotificationProvider(NotificationProvider):
    name = "webhook"

    def validate_configuration(self, *, secret: str = "", config: dict | None = None) -> None:
        if not secret and not (config or {}).get("url"):
            raise ConfigurationNotificationError("Webhook destination requires a URL secret reference")

    def send(self, message: NotificationMessage, *, secret: str = "", config: dict | None = None) -> str:
        config = config or {}
        url = secret or str(config.get("url") or "")
        body = {
            "event": message.event_type,
            "title": message.title,
            "summary": message.summary,
            "severity": message.severity,
            "alertId": message.alert_id,
            "payload": message.payload,
        }
        return _post(url, body)


class SlackNotificationProvider(NotificationProvider):
    name = "slack"

    def validate_configuration(self, *, secret: str = "", config: dict | None = None) -> None:
        if not secret and not (config or {}).get("url"):
            raise ConfigurationNotificationError("Slack destination requires a webhook secret reference")

    def send(self, message: NotificationMessage, *, secret: str = "", config: dict | None = None) -> str:
        url = secret or str((config or {}).get("url") or "")
        text = f"{message.severity} {message.title}\n{message.summary}"
        return _post(url, {"text": text})


class TeamsNotificationProvider(NotificationProvider):
    name = "teams"

    def validate_configuration(self, *, secret: str = "", config: dict | None = None) -> None:
        if not secret and not (config or {}).get("url"):
            raise ConfigurationNotificationError("Teams destination requires a webhook secret reference")

    def send(self, message: NotificationMessage, *, secret: str = "", config: dict | None = None) -> str:
        url = secret or str((config or {}).get("url") or "")
        body = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": message.title,
            "themeColor": "FF0000" if message.severity == "CRITICAL" else "FFA500",
            "title": message.title,
            "text": message.summary,
        }
        return _post(url, body)
