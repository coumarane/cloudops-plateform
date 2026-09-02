from __future__ import annotations

from fastapi import HTTPException

from app.core.config import settings
from app.core.rbac import Principal, require_permission
from app.db.models import CloudEnvironmentRow, GithubRepositoryRow, GithubSecretRow, GithubVariableRow
from app.db.session import SessionLocal
from app.integrations.github import get_scm_provider
from app.integrations.scm.base import ScmRepository
from app.services.github_sync import MASK, _id, mapped_environment, record_audit, utcnow

PRODUCTION = {"NPD", "PRD"}


def _production_environment(session, environment_id: str, github_environment: str) -> str:
    if environment_id:
        row = session.get(CloudEnvironmentRow, environment_id)
        if row is not None:
            return row.environment
    if github_environment.upper() in PRODUCTION:
        return github_environment.upper()
    return ""


def _enforce_production(principal: Principal, environment: str, *, confirmed: bool, reason: str) -> None:
    if environment not in PRODUCTION:
        return
    require_permission(principal, "github_secret:prod_update")
    if not confirmed or not reason.strip():
        raise HTTPException(status_code=400, detail="Production GitHub secret changes require confirmation and a reason")


def replace_secret(
    principal: Principal,
    *,
    repository_id: str,
    name: str,
    value: str,
    scope: str = "repository",
    github_environment: str = "",
    confirmed: bool = False,
    reason: str = "",
    change_ticket: str = "",
    create: bool = False,
) -> GithubSecretRow:
    if not name or not value:
        raise HTTPException(status_code=400, detail="Secret name and value are required")
    session = SessionLocal()
    try:
        repo = session.get(GithubRepositoryRow, repository_id)
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found")
        mapped = mapped_environment(session, repo.id, github_environment) if github_environment else None
        environment = _production_environment(session, mapped.id if mapped else "", github_environment)
        _enforce_production(principal, environment, confirmed=confirmed, reason=reason)
        scm_repo = ScmRepository(
            external_id=repo.github_id,
            organization=repo.organization,
            name=repo.name,
            full_name=repo.full_name,
        )
        get_scm_provider().put_secret(
            repository=scm_repo,
            name=name,
            value=value,
            github_environment=github_environment,
        )
        row_id = _id("ghsec", repo.id, scope, github_environment, name)
        row = session.get(GithubSecretRow, row_id)
        created = row is None
        if created:
            row = GithubSecretRow(
                id=row_id,
                repository_id=repo.id,
                name=name,
                scope=scope,
                github_environment=github_environment,
                organization=repo.organization,
            )
            session.add(row)
        row.updated_at = utcnow()
        if row.created_at is None:
            row.created_at = row.updated_at
        row.cloudops_environment_id = mapped.id if mapped else ""
        action = "GITHUB_SECRET_CREATED" if create or created else "GITHUB_SECRET_REPLACED"
        record_audit(
            session,
            action,
            actor=principal.user,
            object_name=name,
            repository_id=repo.id,
            environment=environment,
            detail=f"ticket={change_ticket}" if change_ticket else "metadata updated",
        )
        session.commit()
        session.refresh(row)
        return row
    except HTTPException:
        session.rollback()
        raise
    finally:
        value = ""
        session.close()


def delete_secret(
    principal: Principal,
    *,
    secret_id: str,
    confirmed: bool = False,
    reason: str = "",
) -> None:
    session = SessionLocal()
    try:
        row = session.get(GithubSecretRow, secret_id)
        if row is None:
            raise HTTPException(status_code=404, detail="GitHub secret metadata not found")
        repo = session.get(GithubRepositoryRow, row.repository_id)
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found")
        mapped = session.get(CloudEnvironmentRow, row.cloudops_environment_id) if row.cloudops_environment_id else None
        environment = mapped.environment if mapped else ""
        _enforce_production(principal, environment, confirmed=confirmed, reason=reason)
        scm_repo = ScmRepository(
            external_id=repo.github_id,
            organization=repo.organization,
            name=repo.name,
            full_name=repo.full_name,
        )
        get_scm_provider().delete_secret(
            repository=scm_repo,
            name=row.name,
            github_environment=row.github_environment,
        )
        record_audit(
            session,
            "GITHUB_SECRET_DELETED",
            actor=principal.user,
            object_name=row.name,
            repository_id=repo.id,
            environment=environment,
        )
        session.delete(row)
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_variable(
    principal: Principal,
    *,
    repository_id: str,
    name: str,
    value: str,
    scope: str = "repository",
    github_environment: str = "",
    sensitive: bool = False,
    confirmed: bool = False,
    reason: str = "",
    create: bool = False,
) -> GithubVariableRow:
    session = SessionLocal()
    try:
        repo = session.get(GithubRepositoryRow, repository_id)
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found")
        mapped = mapped_environment(session, repo.id, github_environment) if github_environment else None
        environment = mapped.environment if mapped else ""
        if environment in PRODUCTION:
            require_permission(principal, "github_secret:prod_update")
            if not confirmed or not reason.strip():
                raise HTTPException(status_code=400, detail="Production GitHub variable changes require confirmation and a reason")
        scm_repo = ScmRepository(
            external_id=repo.github_id,
            organization=repo.organization,
            name=repo.name,
            full_name=repo.full_name,
        )
        get_scm_provider().put_variable(
            repository=scm_repo,
            name=name,
            value=value,
            github_environment=github_environment,
            sensitive=sensitive,
        )
        row_id = _id("ghvar", repo.id, scope, github_environment, name)
        row = session.get(GithubVariableRow, row_id)
        if row is None:
            row = GithubVariableRow(
                id=row_id,
                repository_id=repo.id,
                name=name,
                scope=scope,
                github_environment=github_environment,
                organization=repo.organization,
            )
            session.add(row)
            create = True
        row.sensitive = sensitive
        row.value_masked = MASK if sensitive else value[:48]
        row.updated_at = utcnow()
        row.cloudops_environment_id = mapped.id if mapped else ""
        record_audit(
            session,
            "GITHUB_VARIABLE_CREATED" if create else "GITHUB_VARIABLE_UPDATED",
            actor=principal.user,
            object_name=name,
            repository_id=repo.id,
            environment=environment,
        )
        session.commit()
        session.refresh(row)
        return row
    except HTTPException:
        session.rollback()
        raise
    finally:
        value = ""
        session.close()


def delete_variable(principal: Principal, *, variable_id: str) -> None:
    session = SessionLocal()
    try:
        row = session.get(GithubVariableRow, variable_id)
        if row is None:
            raise HTTPException(status_code=404, detail="GitHub variable not found")
        repo = session.get(GithubRepositoryRow, row.repository_id)
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found")
        scm_repo = ScmRepository(
            external_id=repo.github_id,
            organization=repo.organization,
            name=repo.name,
            full_name=repo.full_name,
        )
        get_scm_provider().delete_variable(
            repository=scm_repo,
            name=row.name,
            github_environment=row.github_environment,
        )
        record_audit(
            session,
            "GITHUB_VARIABLE_DELETED",
            actor=principal.user,
            object_name=row.name,
            repository_id=repo.id,
        )
        session.delete(row)
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    finally:
        session.close()
