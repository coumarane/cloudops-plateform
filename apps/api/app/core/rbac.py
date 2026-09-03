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
    "credential:reveal",
    "certificate:read",
    "certificate:scan",
    "certificate:validate",
    "certificate:ack",
    "github:read",
    "github:sync",
    "github_variable:read",
    "github_variable:update",
    "github_secret:read_metadata",
    "github_secret:create",
    "github_secret:update",
    "github_secret:delete",
    "github_secret:prod_update",
    "github_mapping:read",
    "github_mapping:update",
    "pipeline:read",
    "pipeline:sync",
    "pipeline_mapping:read",
    "pipeline_mapping:update",
    "pipeline:run",
    "pipeline:cancel",
    "pipeline:retry",
    "health:read",
    "health:run_check",
    "incident:read",
    "incident:acknowledge",
    "alert:read",
    "alert:acknowledge",
    "alert:resolve",
    "alert:suppress",
    "alert_rule:read",
    "alert_rule:create",
    "alert_rule:update",
    "alert_rule:delete",
    "notification:read",
    "notification:update",
    "notification:test",
    "maintenance_window:read",
    "maintenance_window:create",
    "maintenance_window:update",
    "maintenance_window:delete",
    "provider:read",
    "provider:create",
    "provider:update",
    "provider:delete",
    "provider:validate",
    "account:read",
    "account:create",
    "account:update",
    "account:delete",
    "account:validate",
    "environment:read",
    "environment:create",
    "environment:update",
    "environment:delete",
    "environment:discover",
    "application:read",
    "application:create",
    "application:update",
    "application:delete",
    "platform_setting:read",
    "platform_setting:update",
    "integration:read",
    "integration:update",
    "integration:sync",
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
            "credential:reveal",
            "certificate:read",
            "certificate:scan",
            "certificate:validate",
            "certificate:ack",
            "github:read",
            "github:sync",
            "github_variable:read",
            "github_variable:update",
            "github_secret:read_metadata",
            "github_secret:create",
            "github_secret:update",
            "github_secret:delete",
            "github_mapping:read",
            "github_mapping:update",
            "pipeline:read",
            "pipeline:sync",
            "pipeline_mapping:read",
            "pipeline_mapping:update",
            "health:read",
            "health:run_check",
            "incident:read",
            "incident:acknowledge",
            "alert:read",
            "alert:acknowledge",
            "alert:suppress",
            "alert_rule:read",
            "notification:read",
            "maintenance_window:read",
            "maintenance_window:create",
            "maintenance_window:update",
            "maintenance_window:delete",
            "provider:read",
            "provider:create",
            "provider:update",
            "provider:validate",
            "account:read",
            "account:create",
            "account:update",
            "account:validate",
            "environment:read",
            "environment:create",
            "environment:update",
            "environment:discover",
            "application:read",
            "application:create",
            "application:update",
            "platform_setting:read",
            "integration:read",
            "integration:update",
            "integration:sync",
        }
    ),
    "OperationsEngineer": frozenset(
        {
            "certificate:read",
            "github:read",
            "github_variable:read",
            "github_secret:read_metadata",
            "pipeline:read",
            "health:read",
            "incident:read",
            "incident:acknowledge",
            "alert:read",
            "alert:acknowledge",
            "alert_rule:read",
            "notification:read",
            "maintenance_window:read",
            "provider:read",
            "account:read",
            "environment:read",
            "application:read",
            "platform_setting:read",
            "integration:read",
        }
    ),
    "SecurityAuditor": frozenset(
        {
            "credential:read",
            "credential:read_history",
            "certificate:read",
            "github:read",
            "github_variable:read",
            "github_secret:read_metadata",
            "github_mapping:read",
            "pipeline:read",
            "pipeline_mapping:read",
            "health:read",
            "incident:read",
            "alert:read",
            "alert_rule:read",
            "notification:read",
            "maintenance_window:read",
            "provider:read",
            "account:read",
            "environment:read",
            "application:read",
            "platform_setting:read",
            "integration:read",
        }
    ),
    "Developer": frozenset(
        {
            "credential:read",
            "certificate:read",
            "github:read",
            "github_variable:read",
            "github_variable:update",
            "github_secret:read_metadata",
            "pipeline:read",
            "health:read",
            "incident:read",
            "alert:read",
            "provider:read",
            "account:read",
            "environment:read",
            "application:read",
        }
    ),
    "ReadOnly": frozenset(
        {
            "credential:read",
            "certificate:read",
            "github:read",
            "github_variable:read",
            "github_secret:read_metadata",
            "github_mapping:read",
            "pipeline:read",
            "pipeline_mapping:read",
            "health:read",
            "incident:read",
            "alert:read",
            "alert_rule:read",
            "notification:read",
            "maintenance_window:read",
            "provider:read",
            "account:read",
            "environment:read",
            "application:read",
            "platform_setting:read",
            "integration:read",
        }
    ),
}

_ROLE_ALIASES = {
    "platformadmin": "PlatformAdmin",
    "platform admin": "PlatformAdmin",
    "devopsengineer": "DevOpsEngineer",
    "devops engineer": "DevOpsEngineer",
    "operationsengineer": "OperationsEngineer",
    "operations engineer": "OperationsEngineer",
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


def require_bootstrap_admin(principal: Principal, permission: str) -> None:
    require_permission(principal, permission)
    mutating = permission.split(":")[-1] not in {"read"}
    if mutating and not settings.bootstrap_admin_allowed():
        raise HTTPException(
            status_code=403,
            detail="Bootstrap administration is disabled outside local development",
        )
