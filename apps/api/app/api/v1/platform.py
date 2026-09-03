from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.listing import listed
from app.api.v1.params import parse_scope
from app.core.config import settings
from app.domain.models import Scope
from app.core.rbac import Principal, principal_from_headers, require_bootstrap_admin, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.db.session import SessionLocal
from app.platform.exceptions import PlatformConflictError, PlatformError, PlatformNotFoundError, PlatformStateError
from app.platform import service as platform
from app.platform.settings_store import list_settings, update_settings

router = APIRouter()


class ProviderWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    providerType: str | None = None
    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None
    authStrategy: str | None = None


class AccountWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    providerId: str | None = None
    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    accountId: str | None = Field(default=None, max_length=32)
    region: str | None = None
    cloudRegion: str | None = None
    cloudRegions: list[str] | None = None
    roleArn: str | None = None
    ramRole: str | None = None
    externalId: str | None = None
    credentialRef: str | None = None
    accountClass: str | None = None
    authStrategy: str | None = None
    enabled: bool | None = None


class EnvironmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accountId: str | None = None
    name: str | None = Field(default=None, max_length=128)
    code: str | None = None
    environmentClass: str | None = None
    description: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None


class ApplicationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=128)
    description: str | None = None
    ownerTeam: str | None = None
    repositoryId: str | None = None
    pipelineId: str | None = None
    enabled: bool | None = None
    environments: list[dict] | None = None


class SettingsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[str, str]


class ClusterMonitorWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ignored: bool | None = None
    monitoringEnabled: bool | None = None


class GithubIntegrationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    appId: str | None = Field(default=None, max_length=64)
    installationId: str | None = Field(default=None, max_length=64)
    organization: str | None = Field(default=None, max_length=128)
    apiUrl: str | None = Field(default=None, max_length=255)
    privateKeyRef: str | None = Field(default=None, max_length=512)
    privateKey: str | None = Field(default=None, max_length=65536)
    webhookSecretRef: str | None = Field(default=None, max_length=512)
    enabled: bool | None = None


class AzureDevOpsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=128)
    organization: str | None = Field(default=None, max_length=128)
    project: str | None = Field(default=None, max_length=128)
    baseUrl: str | None = Field(default=None, max_length=255)
    authRef: str | None = Field(default=None, max_length=512)
    authSecret: str | None = Field(default=None, max_length=65536)
    enabled: bool | None = None


def _filter_scope(items: list[dict], scope: Scope) -> list[dict]:
    filtered = []
    for item in items:
        if scope.provider and item.get("provider") != scope.provider:
            continue
        if scope.region and item.get("region") != scope.region:
            continue
        if scope.environment:
            hosted = item.get("hostedEnvironments")
            if hosted is not None and scope.environment not in hosted:
                continue
            if hosted is None and item.get("environment") != scope.environment:
                continue
        if scope.account and item.get("account") != scope.account:
            continue
        filtered.append(item)
    return filtered


def _payload(data: dict) -> dict:
    from app.core.config import settings

    assert_no_secret_values(walk_strings(data))
    data.setdefault("lastSynced", settings.last_synced)
    return data


def _http(error: PlatformError) -> HTTPException:
    if isinstance(error, PlatformNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, PlatformConflictError):
        return HTTPException(status_code=409, detail=str(error))
    return HTTPException(status_code=400, detail=str(error))


@router.get("/platform/status")
def get_platform_status() -> dict:
    session = SessionLocal()
    try:
        return _payload(platform.platform_status(session))
    finally:
        session.close()


@router.get("/provider-types")
def get_provider_types(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "provider:read")
    return _payload({"items": platform.list_provider_types()})


@router.get("/providers")
def list_managed_providers(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "provider:read")
    session = SessionLocal()
    try:
        items = platform.list_providers(session)
        from app.services.catalog import catalog_service

        if settings.demo_mode and not items:
            return listed(catalog_service.providers())
        return _payload({"items": items})
    finally:
        session.close()


@router.post("/providers")
def create_managed_provider(body: ProviderWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:create")
    if not body.providerType or not body.name:
        raise HTTPException(status_code=400, detail="providerType and name are required")
    session = SessionLocal()
    try:
        return _payload(platform.create_provider(session, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/providers/{provider_id}")
def get_managed_provider(provider_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "provider:read")
    session = SessionLocal()
    try:
        return _payload(platform.get_provider(session, provider_id))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.close()


@router.put("/providers/{provider_id}")
def update_managed_provider(provider_id: str, body: ProviderWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:update")
    session = SessionLocal()
    try:
        return _payload(platform.update_provider(session, provider_id, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.delete("/providers/{provider_id}")
def delete_managed_provider(provider_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:delete")
    session = SessionLocal()
    try:
        platform.delete_provider(session, provider_id, principal.user)
        return _payload({"deleted": True, "id": provider_id})
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/providers/{provider_id}/validate")
def validate_managed_provider(provider_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:validate")
    session = SessionLocal()
    try:
        return _payload(platform.validate_provider_connection(session, provider_id, principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/providers/{provider_id}/discover")
def discover_managed_provider(provider_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:discover")
    session = SessionLocal()
    try:
        from app.db.models import CloudAccountRow
        from sqlalchemy import select

        jobs = []
        for account in session.scalars(select(CloudAccountRow).where(CloudAccountRow.managed_provider_id == provider_id)):
            jobs.append(platform.enqueue_account_discovery(session, account.id, principal.user))
        if not jobs:
            raise HTTPException(status_code=400, detail="Add a cloud account before discovering resources")
        return _payload({"jobs": jobs, "jobId": jobs[0]["jobId"]})
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/accounts")
def list_managed_accounts(scope: Scope = Depends(parse_scope), principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "account:read")
    session = SessionLocal()
    try:
        items = _filter_scope(platform.list_accounts(session), scope)
        if settings.demo_mode and not items:
            from app.services.catalog import catalog_service

            return listed(catalog_service.accounts(scope))
        return _payload({"items": items})
    finally:
        session.close()


@router.post("/accounts")
def create_managed_account(body: AccountWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "account:create")
    if not body.providerId or not body.name or not body.region or not body.accountClass:
        raise HTTPException(status_code=400, detail="providerId, name, region and accountClass are required")
    session = SessionLocal()
    try:
        return _payload(platform.create_account(session, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/accounts/{account_id}")
def get_managed_account(account_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "account:read")
    session = SessionLocal()
    try:
        return _payload(platform.get_account(session, account_id))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.close()


@router.put("/accounts/{account_id}")
def update_managed_account(account_id: str, body: AccountWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "account:update")
    session = SessionLocal()
    try:
        return _payload(platform.update_account(session, account_id, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.delete("/accounts/{account_id}")
def delete_managed_account(account_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "account:delete")
    session = SessionLocal()
    try:
        platform.delete_account(session, account_id, principal.user)
        return _payload({"deleted": True, "id": account_id})
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/accounts/{account_id}/validate")
def validate_managed_account(account_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "account:validate")
    session = SessionLocal()
    try:
        return _payload(platform.validate_account_connection(session, account_id, principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/accounts/{account_id}/discover")
def discover_managed_account(account_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:discover")
    session = SessionLocal()
    try:
        return _payload(platform.enqueue_account_discovery(session, account_id, principal.user))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/environments")
def list_managed_environments(scope: Scope = Depends(parse_scope), principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "environment:read")
    session = SessionLocal()
    try:
        items = _filter_scope(platform.list_environments(session), scope)
        if settings.demo_mode and not items:
            from app.services.catalog import catalog_service

            return listed(catalog_service.environments(scope))
        return _payload({"items": items})
    finally:
        session.close()


@router.post("/environments")
def create_managed_environment(body: EnvironmentWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:create")
    payload = body.model_dump(exclude_none=True)
    payload["code"] = body.environmentClass or body.code
    if not body.accountId or not payload.get("code"):
        raise HTTPException(status_code=400, detail="accountId and environment class are required")
    session = SessionLocal()
    try:
        return _payload(platform.create_environment(session, payload, principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/environments/{environment_id}")
def get_managed_environment(environment_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "environment:read")
    if environment_id.lower() in {"aws", "alibaba"}:
        raise HTTPException(status_code=404, detail="Environment not found")
    session = SessionLocal()
    try:
        return _payload(platform.get_environment_row(session, environment_id))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.close()


@router.put("/environments/{environment_id}")
def update_managed_environment(environment_id: str, body: EnvironmentWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:update")
    session = SessionLocal()
    try:
        return _payload(platform.update_environment(session, environment_id, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.delete("/environments/{environment_id}")
def delete_managed_environment(environment_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:delete")
    session = SessionLocal()
    try:
        platform.delete_environment(session, environment_id, principal.user)
        return _payload({"deleted": True, "id": environment_id})
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/environments/{environment_id}/discover")
def discover_environment(environment_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:discover")
    session = SessionLocal()
    try:
        return _payload(platform.enqueue_environment_job(session, environment_id, "discover", principal.user))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/environments/{environment_id}/health-scan")
def health_scan_environment(environment_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:discover")
    session = SessionLocal()
    try:
        return _payload(platform.enqueue_environment_job(session, environment_id, "health", principal.user))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/environments/{environment_id}/certificate-scan")
def certificate_scan_environment(environment_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:discover")
    session = SessionLocal()
    try:
        return _payload(platform.enqueue_environment_job(session, environment_id, "certificates", principal.user))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/applications")
def list_managed_applications(scope: Scope = Depends(parse_scope), principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "application:read")
    session = SessionLocal()
    try:
        items = _filter_scope(platform.list_applications(session), scope)
        if settings.demo_mode and not items:
            from app.services.catalog import catalog_service

            return listed(catalog_service.applications(scope))
        return _payload({"items": items})
    finally:
        session.close()


@router.post("/applications")
def create_managed_application(body: ApplicationWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "application:create")
    if not body.name:
        raise HTTPException(status_code=400, detail="name is required")
    session = SessionLocal()
    try:
        return _payload(platform.create_application(session, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/applications/{application_id}")
def get_managed_application(application_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "application:read")
    session = SessionLocal()
    try:
        from app.db.models import ManagedApplicationRow
        from app.platform.presenters import application_dump

        row = session.get(ManagedApplicationRow, application_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Application not found")
        return _payload(application_dump(session, row))
    finally:
        session.close()


@router.put("/applications/{application_id}")
def update_managed_application(application_id: str, body: ApplicationWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "application:update")
    session = SessionLocal()
    try:
        return _payload(platform.update_application(session, application_id, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/clusters/{cluster_id}/monitoring")
def update_cluster_monitoring(cluster_id: str, body: ClusterMonitorWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "environment:update")
    session = SessionLocal()
    try:
        return _payload(platform.update_cluster_monitoring(session, cluster_id, ignored=body.ignored, monitoring=body.monitoringEnabled))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.get("/discovery-jobs")
def list_discovery_jobs(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "environment:read")
    session = SessionLocal()
    try:
        return _payload({"items": platform.list_discovery_jobs(session)})
    finally:
        session.close()


@router.get("/discovery-jobs/{job_id}")
def get_discovery_job(job_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "environment:read")
    session = SessionLocal()
    try:
        return _payload(platform.get_discovery_job(session, job_id))
    except PlatformError as error:
        raise _http(error) from error
    finally:
        session.close()


@router.get("/platform/settings")
def get_platform_settings(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "platform_setting:read")
    session = SessionLocal()
    try:
        return _payload({"items": list_settings(session)})
    finally:
        session.close()


@router.put("/platform/settings")
def put_platform_settings(body: SettingsWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "platform_setting:update")
    session = SessionLocal()
    try:
        items = update_settings(session, body.values, principal.user)
        session.commit()
        return _payload({"items": items})
    finally:
        session.close()


@router.get("/admin/integrations")
def list_live_integrations(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "integration:read")
    session = SessionLocal()
    try:
        from app.db.models import GithubIntegrationRow, NotificationDestinationRow, PipelineProviderRow

        items = []
        for row in session.query(GithubIntegrationRow):
            items.append(
                {
                    "id": row.id,
                    "name": f"GitHub {row.organization or row.app_id}",
                    "type": "github",
                    "status": row.status,
                    "scope": row.organization,
                    "note": row.last_error or "GitHub App",
                    "enabled": row.status != "disabled",
                }
            )
        for row in session.query(PipelineProviderRow):
            items.append(
                {
                    "id": row.id,
                    "name": getattr(row, "name", None) or "Azure DevOps",
                    "type": "azure_devops",
                    "status": getattr(row, "status", "configured"),
                    "scope": getattr(row, "organization", "") or "",
                    "note": "Azure DevOps pipelines",
                    "enabled": True,
                }
            )
        for row in session.query(NotificationDestinationRow):
            items.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "type": "notification",
                    "status": "enabled" if row.enabled else "disabled",
                    "scope": row.provider_type,
                    "note": row.description,
                    "enabled": row.enabled,
                }
            )
        if settings.demo_mode and not items:
            from app.services.catalog import catalog_service

            return listed(catalog_service.admin_integrations())
        return _payload({"items": items})
    finally:
        session.close()


@router.post("/admin/integrations/github")
def create_github_integration(body: GithubIntegrationWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "integration:update")
    session = SessionLocal()
    try:
        return _payload(platform.create_github_integration(session, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.put("/admin/integrations/github/{integration_id}")
def update_github_integration(integration_id: str, body: GithubIntegrationWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "integration:update")
    session = SessionLocal()
    try:
        return _payload(platform.update_github_integration(session, integration_id, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/admin/integrations/github/{integration_id}/validate")
def validate_github_integration(integration_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "integration:update")
    session = SessionLocal()
    try:
        return _payload(platform.validate_github_integration(session, integration_id, principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/admin/integrations/azure-devops")
def create_azure_devops_integration(body: AzureDevOpsWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "integration:update")
    session = SessionLocal()
    try:
        return _payload(platform.create_azure_devops_integration(session, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.put("/admin/integrations/azure-devops/{integration_id}")
def update_azure_devops_integration(integration_id: str, body: AzureDevOpsWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "integration:update")
    session = SessionLocal()
    try:
        return _payload(platform.update_azure_devops_integration(session, integration_id, body.model_dump(exclude_none=True), principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()


@router.post("/admin/integrations/azure-devops/{integration_id}/validate")
def validate_azure_devops_integration(integration_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "integration:update")
    session = SessionLocal()
    try:
        return _payload(platform.validate_azure_devops_integration(session, integration_id, principal.user))
    except PlatformError as error:
        session.rollback()
        raise _http(error) from error
    finally:
        session.commit()
        session.close()
