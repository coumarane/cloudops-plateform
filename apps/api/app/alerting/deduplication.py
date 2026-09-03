from __future__ import annotations

from hashlib import sha256

from app.alerting.models import AlertSignal


def fingerprint(signal: AlertSignal) -> str:
    """Stable identity for an underlying issue. Timestamps are excluded."""
    parts = [
        (signal.alert_type or "").strip().upper(),
        (signal.source_type or "").strip().lower(),
        (signal.source_id or "").strip(),
        (signal.environment_id or signal.environment or "").strip(),
    ]
    raw = "|".join(parts)
    return sha256(raw.encode("utf-8")).hexdigest()[:64]
