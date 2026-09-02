from __future__ import annotations

from datetime import datetime, timezone

QUEUED = "QUEUED"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
SKIPPED = "SKIPPED"
UNKNOWN = "UNKNOWN"

CLOUD_STATUSES = (QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED, SKIPPED, UNKNOWN)


def parse_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_run_status(github_status: str | None, conclusion: str | None) -> str:
    status = (github_status or "").lower()
    result = (conclusion or "").lower()
    if status in {"queued", "waiting", "requested", "pending"}:
        return QUEUED
    if status in {"in_progress", "running"}:
        return RUNNING
    if status in {"completed", "complete"}:
        if result in {"success", "succeeded"}:
            return SUCCEEDED
        if result in {"failure", "failed", "timed_out", "startup_failure", "action_required"}:
            return FAILED
        if result in {"cancelled", "canceled"}:
            return CANCELLED
        if result in {"skipped", "neutral", "stale"}:
            return SKIPPED
        return UNKNOWN
    if not status and not result:
        return UNKNOWN
    return UNKNOWN


def duration_seconds(started: datetime | None, completed: datetime | None) -> int | None:
    if started is None or completed is None:
        return None
    delta = completed - started
    return max(0, int(delta.total_seconds()))
