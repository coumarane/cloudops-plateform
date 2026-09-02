from __future__ import annotations

from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    """Provider-neutral certificate notification channel."""

    name = "base"

    @abstractmethod
    def send(self, event_type: str, payload: dict[str, object]) -> None:
        raise NotImplementedError
