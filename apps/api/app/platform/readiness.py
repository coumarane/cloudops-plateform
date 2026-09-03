from __future__ import annotations

READYNESS = (
    "NOT_CONFIGURED",
    "CREDENTIAL_MISSING",
    "VALIDATION_FAILED",
    "READY",
    "DISCOVERY_PENDING",
    "ACTIVE",
    "DISABLED",
)


def account_readiness(account) -> str:
    if not getattr(account, "enabled", True):
        return "DISABLED"
    if (account.validation_status or "").upper() in {"FAILED", "INVALID", "ERROR"}:
        return "VALIDATION_FAILED"
    has_auth = bool(account.role_arn or account.ram_role or account.credential_ref)
    if not has_auth:
        return "CREDENTIAL_MISSING"
    if account.last_validated_at is None:
        return "NOT_CONFIGURED"
    return "READY"


def environment_readiness(environment, account) -> str:
    if not environment.enabled:
        return "DISABLED"
    base = account_readiness(account)
    if base in {"DISABLED", "CREDENTIAL_MISSING", "VALIDATION_FAILED", "NOT_CONFIGURED"}:
        return base
    if environment.discovery_active:
        return "ACTIVE"
    if environment.last_attempted_scan_at and not environment.discovery_active:
        return "DISCOVERY_PENDING"
    return "READY"
