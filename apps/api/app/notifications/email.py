from __future__ import annotations

from app.core.logging import get_logger
from app.notifications.base import NotificationProvider
from app.notifications.exceptions import ConfigurationNotificationError
from app.notifications.models import NotificationMessage

logger = get_logger(__name__)


class LogNotificationProvider(NotificationProvider):
    name = "log"

    def send(self, message: NotificationMessage, *, secret: str = "", config: dict | None = None) -> str:
        logger.info(
            "notification event=%s title=%s severity=%s destination=%s",
            message.event_type,
            message.title,
            message.severity,
            message.destination_id,
        )
        return f"log-{message.alert_id or 'none'}"


class EmailNotificationProvider(NotificationProvider):
    name = "email"

    def validate_configuration(self, *, secret: str = "", config: dict | None = None) -> None:
        config = config or {}
        if not (config.get("to") or config.get("recipient")):
            raise ConfigurationNotificationError("Email destination requires a recipient")

    def send(self, message: NotificationMessage, *, secret: str = "", config: dict | None = None) -> str:
        config = config or {}
        recipient = str(config.get("to") or config.get("recipient") or "")
        host = str(config.get("smtp_host") or "")
        if not recipient:
            raise ConfigurationNotificationError("Email destination requires a recipient")
        if host:
            import smtplib
            from email.message import EmailMessage

            mail = EmailMessage()
            mail["Subject"] = f"[{message.severity}] {message.title}"
            mail["From"] = str(config.get("from") or "cloudops@localhost")
            mail["To"] = recipient
            mail.set_content(message.summary or message.title)
            with smtplib.SMTP(host, int(config.get("smtp_port") or 25), timeout=10) as smtp:
                if secret:
                    smtp.login(str(config.get("smtp_user") or ""), secret)
                smtp.send_message(mail)
            return f"smtp-{recipient}"
        logger.info("email notification queued recipient=%s event=%s", recipient, message.event_type)
        return f"email-{recipient}"
