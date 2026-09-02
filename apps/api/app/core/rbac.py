from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.core.config import settings

PERMISSIONS = {
    "credential:read",
    "credential:create",
    "credential:update",
    "credential:validate",
    "credential:rotate",
    "credential:read_history",
    "credential:prod_update",
    "certificate:read",
    "certificate:scan",
    "certificate:validate",
    "certificate:ack",
}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "PlatformAdmin": frozenset(PERMISSIONS),
    "DevOpsEngineer": frozenset(
        {
            "credential:read",
            "credential:create",
            "credential:update",
            "credential:validate",
            "credential:rotate",
            "credential:read_history",
            "certificate:read",
            "certificate:scan",
            "certificate:validate",
            "certificate:ack",
        }
    ),
    "SecurityAuditor": frozenset({"credential:read", "credential:read_history", "certificate:read"}),
    "Developer": frozenset({"credential:read", "certificate:read"}),
    "ReadOnly": frozenset({"credential:read", "certificate:read"}),
}

_ROLE_ALIASES = {
    "platformadmin": "PlatformAdmin",
    "platform admin": "PlatformAdmin",
    "devopsengineer": "DevOpsEngineer",
    "devops engineer": "DevOpsEngineer",
    "securityauditor": "SecurityAuditor",
    "security auditor": "SecurityAuditor",
    "developer": "Developer",
    "readonly": "ReadOnly",
    "read-only": "ReadOnly",
    "read only": "ReadOnly",
}


@dataclass(frozen=True)
class Principal:
    user: str
    role: str
    permissions: frozenset[str]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def normalize_role(value: str) -> str:
    mapped = _ROLE_ALIASES.get(value.strip().lower())
    if mapped is None:
        raise HTTPException(status_code=403, detail="Unknown CloudOps role")
    return mapped


def principal_from_headers(
    x_cloudops_user: str | None = Header(default=None, alias="X-CloudOps-User"),
    x_cloudops_role: str | None = Header(default=None, alias="X-CloudOps-Role"),
) -> Principal:
    user = (x_cloudops_user or "").strip()
    role_raw = (x_cloudops_role or "").strip()
    if settings.require_auth and not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = user or settings.default_user
    role = normalize_role(role_raw or settings.default_role)
    return Principal(user=user, role=role, permissions=ROLE_PERMISSIONS[role])


def require_permission(principal: Principal, permission: str) -> None:
    if not principal.can(permission):
        raise HTTPException(status_code=403, detail="Permission denied")
