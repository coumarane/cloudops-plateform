from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.notifications.base import NotificationProvider

logger = get_logger(__name__)


class SlackProvider(NotificationProvider):
    name = "slack"

    def send(self, event_type: str, payload: dict[str, object]) -> None:
        webhook = settings.slack_webhook_url
        if not webhook:
            logger.info("slack webhook not configured event=%s domain=%s", event_type, payload.get("domain"))
            return
        try:
            import json
            import urllib.request

            body = json.dumps(
                {
                    "text": (
                        f"{event_type}: {payload.get('domain')} "
                        f"status={payload.get('status')} days={payload.get('days_remaining')}"
                    )
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                webhook,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                response.read()
        except Exception:
            logger.warning("slack notification failed event=%s", event_type)
