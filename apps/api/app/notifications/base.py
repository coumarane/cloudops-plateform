from __future__ import annotations

from abc import ABC, abstractmethod

from app.notifications.models import NotificationMessage


class NotificationProvider(ABC):
    """Provider-neutral notification channel. Alert modules must not call this directly."""

    name = "base"

    @abstractmethod
    def send(self, message: NotificationMessage, *, secret: str = "", config: dict | None = None) -> str:
        """Return an external message id. Raise NotificationError on failure."""
        raise NotImplementedError

    def validate_configuration(self, *, secret: str = "", config: dict | None = None) -> None:
        return None
