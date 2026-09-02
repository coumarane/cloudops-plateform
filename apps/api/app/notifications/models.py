from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NotificationMessage:
    event_type: str
    title: str
    summary: str
    severity: str
    payload: dict[str, object] = field(default_factory=dict)
    destination_id: str = ""
    alert_id: str = ""
