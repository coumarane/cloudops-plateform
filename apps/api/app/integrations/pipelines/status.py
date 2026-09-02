from __future__ import annotations

QUEUED = "QUEUED"
WAITING = "WAITING"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
SKIPPED = "SKIPPED"
PARTIAL = "PARTIAL"
UNKNOWN = "UNKNOWN"

CLOUD_STATUSES = (
    QUEUED,
    WAITING,
    RUNNING,
    SUCCEEDED,
    FAILED,
    CANCELLED,
    SKIPPED,
    PARTIAL,
    UNKNOWN,
)

ACTIVE_STATUSES = {QUEUED, WAITING, RUNNING}
FAILED_STATUSES = {FAILED}
SUCCESS_STATUSES = {SUCCEEDED}


def normalize_github(github_status: str | None, conclusion: str | None) -> str:
    status = (github_status or "").lower()
    result = (conclusion or "").lower()
    if status in {"waiting"}:
        return WAITING
    if status in {"queued", "requested", "pending"}:
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
    if status in CLOUD_STATUSES:
        return status
    if not status and not result:
        return UNKNOWN
    return UNKNOWN


def normalize_azure(state: str | None, result: str | None) -> str:
    status = (state or "").lower()
    outcome = (result or "").lower()
    if status in {"notstarted", "not_started", "queued", "pending"}:
        return QUEUED
    if status in {"waiting"}:
        return WAITING
    if status in {"inprogress", "in_progress", "running", "cancelling", "canceling"}:
        if outcome in {"canceled", "cancelled"}:
            return CANCELLED
        return RUNNING
    if status in {"completed", "complete", "finished"}:
        if outcome in {"succeeded", "success"}:
            return SUCCEEDED
        if outcome in {"failed", "failure"}:
            return FAILED
        if outcome in {"canceled", "cancelled"}:
            return CANCELLED
        if outcome in {"skipped"}:
            return SKIPPED
        if outcome in {"succeededwithissues", "succeeded_with_issues", "partiallysucceeded", "partial"}:
            return PARTIAL
        return UNKNOWN
    if status in {item.lower() for item in CLOUD_STATUSES}:
        return status.upper()
    return UNKNOWN


def catalog_result(status: str) -> str:
    if status == SUCCEEDED:
        return "Succeeded"
    if status in {FAILED, CANCELLED}:
        return "Failed"
    if status == PARTIAL:
        return "Failed"
    return "Running"
