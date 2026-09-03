from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    ApplicationEnvironmentBindingRow,
    CloudAccountRow,
    CloudEnvironmentRow,
    CloudProviderRow,
    EksClusterRow,
    ManagedApplicationRow,
    ManagedProviderRow,
    PlatformAuditRow,
    PlatformJobRow,
    PlatformRegionRow,
)
from app.db.repository import utcnow
from app.platform.bindings import account_binding, environments_for_account
from app.platform.exceptions import PlatformConflictError, PlatformNotFoundError, PlatformStateError
from app.platform.ids import new_id
from app.platform.presenters import (
    account_dump,
    application_dump,
    environment_dump,
    provider_dump,
)
from app.platform.readiness import account_readiness, environment_readiness
from app.providers.factory import provider_adapter
from app.services.jobs import enqueue_job
from app.topology.models import environment_scope_id

AUTH_STRATEGIES = {
    "AWS": ("AssumeRole", "IAM"),
    "Alibaba": ("RAM", "STS", "AccessKey"),
}
ACCOUNT_CLASSES = {"NONPROD": "NONPROD", "PROD": "PROD", "NON-PRODUCTION": "NONPROD", "PRODUCTION": "PROD"}
ENVIRONMENT_CLASSES = {"DEV", "INT", "TST", "INT/TST", "UAT", "NPD", "PRD"}


def _normalize_env(value: str) -> str:
    raw = value.strip().upper()
    if raw in {"INT", "TST", "INT-TST", "INT_TST"}:
        return "INT/TST"
    if raw not in ENVIRONMENT_CLASSES and raw != "INT/TST":
        raise PlatformStateError("Unknown environment class")
    return "INT/TST" if raw in {"INT", "TST"} else raw


def _normalize_account_class(value: str) -> str:
    mapped = ACCOUNT_CLASSES.get(value.strip().upper().replace(" ", "-"), value.strip().upper())
    if mapped not in {"NONPROD", "PROD"}:
        raise PlatformStateError("Account class must be NONPROD or PROD")
    return mapped


def _audit(session: Session, action: str, actor: str, object_name: str, detail: str = "") -> None:
    session.add(
        PlatformAuditRow(
            id=new_id("aud"),
            action=action,
            actor=actor,
            object_name=object_name,
            detail=detail[:2000],
            created_at=utcnow(),
        )
    )


def _ensure_type_rows(session: Session, provider_type: str, region: str, cloud_region: str) -> None:
    if session.get(CloudProviderRow, provider_type) is None:
        session.add(CloudProviderRow(id=provider_type, name=provider_type))
        session.flush()
    region_id = f"{provider_type.lower()}-{region.lower()}"
    row = session.get(PlatformRegionRow, region_id)
    if row is None:
        session.add(
            PlatformRegionRow(
                id=region_id,
                provider=provider_type,
                name=region,
                cloud_region=cloud_region,
            )
        )
        session.flush()


def list_provider_types() -> list[dict]:
    return [
        {"id": "AWS", "name": "AWS", "platform": "EKS", "authStrategies": list(AUTH_STRATEGIES["AWS"])},
        {"id": "Alibaba", "name": "Alibaba Cloud", "platform": "ACK", "authStrategies": list(AUTH_STRATEGIES["Alibaba"])},
    ]


def list_providers(session: Session) -> list[dict]:
    rows = list(session.scalars(select(ManagedProviderRow).order_by(ManagedProviderRow.name)))
    return [provider_dump(session, row) for row in rows]


def get_provider(session: Session, provider_id: str) -> dict:
    row = session.get(ManagedProviderRow, provider_id)
    if row is None:
        raise PlatformNotFoundError("Provider not found")
    payload = provider_dump(session, row)
    payload["accountsDetail"] = [
        account_dump(session, item)
        for item in session.scalars(select(CloudAccountRow).where(CloudAccountRow.managed_provider_id == row.id))
    ]
    payload["environmentsDetail"] = [
        environment_dump(session, item)
        for item in session.scalars(select(CloudEnvironmentRow))
        if session.get(CloudAccountRow, item.account_id)
        and session.get(CloudAccountRow, item.account_id).managed_provider_id == row.id
    ]
    return payload


def create_provider(session: Session, body: dict, actor: str) -> dict:
    provider_type = body["providerType"]
    if provider_type not in AUTH_STRATEGIES:
        raise PlatformStateError("Unsupported provider type")
    name = body["name"].strip()
    existing = session.scalar(select(ManagedProviderRow).where(ManagedProviderRow.name == name))
    if existing is not None:
        raise PlatformConflictError("A provider with this name already exists")
    now = utcnow()
    row = ManagedProviderRow(
        id=new_id("prv"),
        name=name,
        provider_type=provider_type,
        description=body.get("description") or "",
        enabled=bool(body.get("enabled", True)),
        auth_strategy=body.get("authStrategy") or AUTH_STRATEGIES[provider_type][0],
        status="NOT_CONFIGURED",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    _ensure_type_rows(
        session,
        provider_type,
        "EMEA" if provider_type == "AWS" else "China",
        "eu-west-1" if provider_type == "AWS" else "cn-hangzhou",
    )
    _audit(session, "PROVIDER_CREATED", actor, row.name)
    session.flush()
    return provider_dump(session, row)


def update_provider(session: Session, provider_id: str, body: dict, actor: str) -> dict:
    row = session.get(ManagedProviderRow, provider_id)
    if row is None:
        raise PlatformNotFoundError("Provider not found")
    if "name" in body and body["name"]:
        row.name = body["name"].strip()
    if "description" in body:
        row.description = body["description"] or ""
    if "enabled" in body:
        row.enabled = bool(body["enabled"])
        row.status = "DISABLED" if not row.enabled else row.status
    if "authStrategy" in body and body["authStrategy"]:
        row.auth_strategy = body["authStrategy"]
    row.updated_at = utcnow()
    _audit(session, "PROVIDER_UPDATED", actor, row.name)
    session.flush()
    return provider_dump(session, row)


def delete_provider(session: Session, provider_id: str, actor: str) -> None:
    row = session.get(ManagedProviderRow, provider_id)
    if row is None:
        raise PlatformNotFoundError("Provider not found")
    accounts = list(session.scalars(select(CloudAccountRow).where(CloudAccountRow.managed_provider_id == provider_id)))
    if accounts:
        raise PlatformStateError("Delete unused accounts before removing the provider")
    _audit(session, "PROVIDER_DELETED", actor, row.name)
    session.delete(row)


def list_accounts(session: Session) -> list[dict]:
    return [account_dump(session, row) for row in session.scalars(select(CloudAccountRow).order_by(CloudAccountRow.alias))]


def get_account(session: Session, account_id: str) -> dict:
    row = session.get(CloudAccountRow, account_id)
    if row is None:
        raise PlatformNotFoundError("Account not found")
    payload = account_dump(session, row)
    payload["environmentsDetail"] = [
        environment_dump(session, item)
        for item in session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == row.id))
    ]
    return payload


def create_account(session: Session, body: dict, actor: str) -> dict:
    provider = session.get(ManagedProviderRow, body["providerId"])
    if provider is None:
        raise PlatformNotFoundError("Provider not found")
    alias = body["name"].strip().lower().replace(" ", "-")
    if session.scalar(select(CloudAccountRow).where(CloudAccountRow.alias == alias)):
        raise PlatformConflictError("An account with this name already exists")
    region = body["region"]
    cloud = body.get("cloudRegion") or ("cn-hangzhou" if provider.provider_type == "Alibaba" else "eu-west-1")
    account_class = _normalize_account_class(body["accountClass"])
    _ensure_type_rows(session, provider.provider_type, region, cloud)
    row = CloudAccountRow(
        id=new_id("acct"),
        provider=provider.provider_type,
        platform_region=region,
        cloud_region=cloud,
        alias=alias,
        account_id=body.get("accountId") or "",
        role_arn=body.get("roleArn") or "",
        external_id=body.get("externalId") or "",
        account_class=account_class,
        readonly=account_class == "PROD",
        session_name="cloudops-admin",
        credential_ref=body.get("credentialRef") or "",
        managed_provider_id=provider.id,
        enabled=bool(body.get("enabled", True)),
        display_name=body["name"].strip(),
        description=body.get("description") or "",
        auth_strategy=body.get("authStrategy") or provider.auth_strategy,
        ram_role=body.get("ramRole") or "",
        cloud_regions_json=str(body.get("cloudRegions") or []),
    )
    if isinstance(body.get("cloudRegions"), list):
        import json

        row.cloud_regions_json = json.dumps(body["cloudRegions"])
        if body["cloudRegions"]:
            row.cloud_region = str(body["cloudRegions"][0])
    session.add(row)
    _audit(session, "ACCOUNT_CREATED", actor, row.display_name)
    session.flush()
    return account_dump(session, row)


def update_account(session: Session, account_id: str, body: dict, actor: str) -> dict:
    row = session.get(CloudAccountRow, account_id)
    if row is None:
        raise PlatformNotFoundError("Account not found")
    mapping = {
        "name": "display_name",
        "description": "description",
        "accountId": "account_id",
        "roleArn": "role_arn",
        "externalId": "external_id",
        "credentialRef": "credential_ref",
        "ramRole": "ram_role",
        "authStrategy": "auth_strategy",
        "region": "platform_region",
        "cloudRegion": "cloud_region",
    }
    for key, field in mapping.items():
        if key in body and body[key] is not None:
            setattr(row, field, body[key])
    if "enabled" in body:
        row.enabled = bool(body["enabled"])
    if "accountClass" in body:
        row.account_class = _normalize_account_class(body["accountClass"])
        row.readonly = row.account_class == "PROD"
    _audit(session, "ACCOUNT_UPDATED", actor, row.display_name or row.alias)
    session.flush()
    return account_dump(session, row)


def delete_account(session: Session, account_id: str, actor: str) -> None:
    row = session.get(CloudAccountRow, account_id)
    if row is None:
        raise PlatformNotFoundError("Account not found")
    envs = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account_id)))
    clusters = session.query(EksClusterRow).filter(EksClusterRow.account_alias == row.alias, EksClusterRow.present.is_(True)).count()
    if envs or clusters:
        raise PlatformStateError("Delete unused environments and discovered clusters before removing the account")
    _audit(session, "ACCOUNT_DELETED", actor, row.display_name or row.alias)
    session.delete(row)


def list_environments(session: Session) -> list[dict]:
    return [environment_dump(session, row) for row in session.scalars(select(CloudEnvironmentRow))]


def get_environment_row(session: Session, environment_id: str) -> dict:
    row = session.get(CloudEnvironmentRow, environment_id)
    if row is None:
        raise PlatformNotFoundError("Environment not found")
    return environment_dump(session, row)


def create_environment(session: Session, body: dict, actor: str) -> dict:
    account = session.get(CloudAccountRow, body["accountId"])
    if account is None:
        raise PlatformNotFoundError("Account not found")
    environment = _normalize_env(body["code"] if body.get("code") else body["name"])
    env_id = environment_scope_id(account.alias, environment)
    if session.get(CloudEnvironmentRow, env_id) is not None:
        raise PlatformConflictError("Environment already exists for this account")
    row = CloudEnvironmentRow(
        id=env_id,
        account_id=account.id,
        provider=account.provider,
        platform_region=account.platform_region,
        cloud_region=account.cloud_region,
        environment=environment,
        account_alias=account.alias,
        readonly=account.readonly or environment == "PRD",
        enabled=bool(body.get("enabled", True)),
        name=body.get("name") or f"{account.display_name or account.alias} {environment}",
        code=environment_scope_id(account.alias, environment),
        description=body.get("description") or "",
        readiness_status="NOT_CONFIGURED",
    )
    row.readiness_status = environment_readiness(row, account)
    session.add(row)
    _audit(session, "ENVIRONMENT_CREATED", actor, row.name)
    session.flush()
    return environment_dump(session, row)


def update_environment(session: Session, environment_id: str, body: dict, actor: str) -> dict:
    row = session.get(CloudEnvironmentRow, environment_id)
    if row is None:
        raise PlatformNotFoundError("Environment not found")
    if "name" in body and body["name"]:
        row.name = body["name"]
    if "description" in body:
        row.description = body["description"] or ""
    if "enabled" in body:
        row.enabled = bool(body["enabled"])
    account = session.get(CloudAccountRow, row.account_id)
    if account is not None:
        row.readiness_status = environment_readiness(row, account)
    _audit(session, "ENVIRONMENT_UPDATED", actor, row.name or row.id)
    session.flush()
    return environment_dump(session, row)


def delete_environment(session: Session, environment_id: str, actor: str) -> None:
    row = session.get(CloudEnvironmentRow, environment_id)
    if row is None:
        raise PlatformNotFoundError("Environment not found")
    clusters = session.query(EksClusterRow).filter(EksClusterRow.environment_id == row.id, EksClusterRow.present.is_(True)).count()
    if clusters:
        raise PlatformStateError("Discovered clusters still present for this environment")
    _audit(session, "ENVIRONMENT_DELETED", actor, row.name or row.id)
    session.delete(row)


def _binding_for_account(session: Session, account: CloudAccountRow):
    envs = environments_for_account(
        account,
        list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id))),
    )
    return account_binding(account, envs)


def validate_account_connection(session: Session, account_id: str, actor: str) -> dict:
    row = session.get(CloudAccountRow, account_id)
    if row is None:
        raise PlatformNotFoundError("Account not found")
    adapter = provider_adapter(row.provider)
    result = adapter.validate_connection(_binding_for_account(session, row))
    row.last_validated_at = utcnow()
    row.validation_status = "HEALTHY" if result.connected else "FAILED"
    row.last_error_class = result.error_category
    row.identity_account = result.account_id
    row.identity_principal = result.principal
    provider = session.get(ManagedProviderRow, row.managed_provider_id) if row.managed_provider_id else None
    if provider is not None:
        provider.last_validated_at = row.last_validated_at
        provider.validation_status = row.validation_status
        provider.error_category = result.error_category
        provider.identity_account = result.account_id
        provider.identity_principal = result.principal
        provider.status = "READY" if result.connected and provider.enabled else ("VALIDATION_FAILED" if not result.connected else provider.status)
        provider.updated_at = utcnow()
    for env in session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == row.id)):
        env.readiness_status = environment_readiness(env, row)
        env.last_error = "" if result.connected else result.detail
        env.last_error_class = result.error_category
    _audit(session, "ACCOUNT_VALIDATED", actor, row.display_name or row.alias, result.detail or result.principal)
    session.flush()
    return {
        "connected": result.connected,
        "account": result.account_id,
        "principal": result.principal,
        "region": result.region,
        "errorCategory": result.error_category,
        "detail": result.detail,
        "status": row.validation_status,
        "validatedAt": row.last_validated_at.isoformat(),
    }


def validate_provider_connection(session: Session, provider_id: str, actor: str) -> dict:
    row = session.get(ManagedProviderRow, provider_id)
    if row is None:
        raise PlatformNotFoundError("Provider not found")
    accounts = list(session.scalars(select(CloudAccountRow).where(CloudAccountRow.managed_provider_id == provider_id)))
    if not accounts:
        raise PlatformStateError("Add a cloud account before validating the provider")
    last = None
    for account in accounts:
        last = validate_account_connection(session, account.id, actor)
        if last["connected"]:
            break
    return last or {"connected": False, "detail": "No accounts"}


def enqueue_account_discovery(session: Session, account_id: str, actor: str) -> dict:
    row = session.get(CloudAccountRow, account_id)
    if row is None:
        raise PlatformNotFoundError("Account not found")
    adapter = provider_adapter(row.provider)
    job = enqueue_job(
        adapter.discovery_job_kind,
        target_id=row.id,
        provider=row.provider,
        platform_region=row.platform_region,
        environment=row.account_class,
    )
    _audit(session, "ACCOUNT_DISCOVERY_STARTED", actor, row.display_name or row.alias, job.id)
    return {"jobId": job.id, "status": job.status.upper(), "kind": job.kind, "detail": "Cluster discovery started"}


def enqueue_environment_job(session: Session, environment_id: str, action: str, actor: str) -> dict:
    row = session.get(CloudEnvironmentRow, environment_id)
    if row is None:
        raise PlatformNotFoundError("Environment not found")
    adapter = provider_adapter(row.provider)
    kinds = {
        "discover": adapter.discovery_job_kind,
        "health": adapter.health_job_kind,
        "certificates": adapter.certificate_job_kind,
    }
    kind = kinds.get(action)
    if not kind:
        raise PlatformStateError("Unknown environment action")
    job = enqueue_job(
        kind,
        target_id=row.id,
        provider=row.provider,
        platform_region=row.platform_region,
        environment=row.environment,
    )
    _audit(session, "ENVIRONMENT_JOB_STARTED", actor, row.name or row.id, f"{action}:{job.id}")
    return {"jobId": job.id, "status": job.status.upper(), "kind": job.kind, "detail": f"{action} started"}


def list_discovery_jobs(session: Session) -> list[dict]:
    rows = list(session.scalars(select(PlatformJobRow).order_by(PlatformJobRow.created_at.desc()).limit(200)))
    status_map = {
        "queued": "QUEUED",
        "running": "RUNNING",
        "succeeded": "SUCCEEDED",
        "partial": "PARTIAL",
        "failed": "FAILED",
    }
    items = []
    for row in rows:
        items.append(
            {
                "id": row.id,
                "job": row.name,
                "provider": row.provider,
                "account": row.target_id,
                "environment": row.environment,
                "type": row.kind,
                "started": row.started_at.isoformat() if row.started_at else row.created_at.isoformat(),
                "finished": row.finished_at.isoformat() if row.finished_at else None,
                "status": status_map.get(row.status, row.status.upper()),
                "resourcesFound": row.resources_found,
                "errors": row.error_count,
                "detail": row.detail,
                "correlationId": row.correlation_id,
            }
        )
    return items


def get_discovery_job(session: Session, job_id: str) -> dict:
    row = session.get(PlatformJobRow, job_id)
    if row is None:
        raise PlatformNotFoundError("Job not found")
    matches = [item for item in list_discovery_jobs(session) if item["id"] == job_id]
    return matches[0]


def list_applications(session: Session) -> list[dict]:
    return [application_dump(session, row) for row in session.scalars(select(ManagedApplicationRow))]


def create_application(session: Session, body: dict, actor: str) -> dict:
    now = utcnow()
    row = ManagedApplicationRow(
        id=new_id("app"),
        name=body["name"].strip(),
        description=body.get("description") or "",
        owner_team=body.get("ownerTeam") or "",
        repository_id=body.get("repositoryId") or "",
        pipeline_id=body.get("pipelineId") or "",
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    for item in body.get("environments") or []:
        session.add(
            ApplicationEnvironmentBindingRow(
                id=new_id("map"),
                application_id=row.id,
                environment_id=item.get("environmentId") or "",
                cluster_id=item.get("clusterId") or "",
                namespace=item.get("namespace") or "",
                workload=item.get("workload") or "",
                health_endpoint=item.get("healthEndpoint") or "",
            )
        )
    _audit(session, "APPLICATION_CREATED", actor, row.name)
    session.flush()
    return application_dump(session, row)


def update_application(session: Session, application_id: str, body: dict, actor: str) -> dict:
    row = session.get(ManagedApplicationRow, application_id)
    if row is None:
        raise PlatformNotFoundError("Application not found")
    for key, field in {"name": "name", "description": "description", "ownerTeam": "owner_team", "repositoryId": "repository_id", "pipelineId": "pipeline_id"}.items():
        if key in body and body[key] is not None:
            setattr(row, field, body[key])
    if "enabled" in body:
        row.enabled = bool(body["enabled"])
    if "environments" in body:
        existing = list(session.scalars(select(ApplicationEnvironmentBindingRow).where(ApplicationEnvironmentBindingRow.application_id == row.id)))
        for item in existing:
            session.delete(item)
        session.flush()
        for item in body["environments"] or []:
            session.add(
                ApplicationEnvironmentBindingRow(
                    id=new_id("map"),
                    application_id=row.id,
                    environment_id=item.get("environmentId") or "",
                    cluster_id=item.get("clusterId") or "",
                    namespace=item.get("namespace") or "",
                    workload=item.get("workload") or "",
                    health_endpoint=item.get("healthEndpoint") or "",
                )
            )
    row.updated_at = utcnow()
    _audit(session, "APPLICATION_UPDATED", actor, row.name)
    session.flush()
    return application_dump(session, row)


def update_cluster_monitoring(session: Session, cluster_id: str, *, ignored: bool | None = None, monitoring: bool | None = None) -> dict:
    row = session.get(EksClusterRow, cluster_id)
    if row is None:
        raise PlatformNotFoundError("Cluster not found")
    if ignored is not None:
        row.ignored = ignored
    if monitoring is not None:
        row.monitoring_enabled = monitoring
    session.flush()
    return {"id": row.id, "ignored": row.ignored, "monitoringEnabled": row.monitoring_enabled}


def platform_status(session: Session) -> dict:
    from app.platform.presenters import configured_provider_count, data_source

    count = configured_provider_count(session)
    return {
        "demoMode": settings.demo_mode,
        "dataSource": data_source(session),
        "bootstrapAdmin": settings.bootstrap_admin_allowed(),
        "onboarding": not settings.demo_mode and count == 0,
        "configuredProviders": count,
        "providerStub": settings.provider_stub,
        "appEnvironment": settings.app_environment,
    }


def _store_secret_ref(reference: str, secret: str | None, existing: str = "") -> str:
    if not secret:
        return existing or reference
    from app.secrets.factory import secret_backend

    backend = secret_backend()
    try:
        backend.store_secret(reference, secret)
    except Exception:
        backend.replace_secret(reference, secret)
    return reference


def create_github_integration(session: Session, body: dict, actor: str) -> dict:
    from app.db.models import GithubIntegrationRow
    from app.services.github_sync import _id

    app_id = (body.get("appId") or "").strip()
    installation = (body.get("installationId") or "").strip()
    organization = (body.get("organization") or "").strip()
    if not app_id or not installation:
        raise PlatformStateError("GitHub App id and installation id are required")
    row_id = _id("ghi", app_id, installation)
    existing = session.get(GithubIntegrationRow, row_id)
    if existing is not None:
        raise PlatformConflictError("GitHub App integration already exists")
    ref = _store_secret_ref(f"github/{app_id}/private-key", body.get("privateKey"), body.get("privateKeyRef") or "")
    now = utcnow()
    row = GithubIntegrationRow(
        id=row_id,
        app_id=app_id,
        installation_id=installation,
        organization=organization,
        api_url=body.get("apiUrl") or "https://api.github.com",
        private_key_ref=ref,
        webhook_secret_ref=body.get("webhookSecretRef") or "",
        status="configured" if ref else "pending",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    _audit(session, "GITHUB_INTEGRATION_CREATED", actor, organization or app_id)
    session.flush()
    return _github_dump(row)


def update_github_integration(session: Session, integration_id: str, body: dict, actor: str) -> dict:
    from app.db.models import GithubIntegrationRow

    row = session.get(GithubIntegrationRow, integration_id)
    if row is None:
        raise PlatformNotFoundError("GitHub integration not found")
    if body.get("organization") is not None:
        row.organization = body["organization"]
    if body.get("apiUrl"):
        row.api_url = body["apiUrl"]
    if body.get("installationId"):
        row.installation_id = body["installationId"]
    if body.get("appId"):
        row.app_id = body["appId"]
    if body.get("privateKey") or body.get("privateKeyRef"):
        row.private_key_ref = _store_secret_ref(row.private_key_ref or f"github/{row.app_id}/private-key", body.get("privateKey"), body.get("privateKeyRef") or row.private_key_ref)
    if body.get("webhookSecretRef") is not None:
        row.webhook_secret_ref = body["webhookSecretRef"] or ""
    if body.get("enabled") is False:
        row.status = "disabled"
    elif body.get("enabled") is True and row.status == "disabled":
        row.status = "configured"
    row.updated_at = utcnow()
    _audit(session, "GITHUB_INTEGRATION_UPDATED", actor, row.organization or row.app_id)
    session.flush()
    return _github_dump(row)


def validate_github_integration(session: Session, integration_id: str, actor: str) -> dict:
    from app.db.models import GithubIntegrationRow

    row = session.get(GithubIntegrationRow, integration_id)
    if row is None:
        raise PlatformNotFoundError("GitHub integration not found")
    if not row.app_id or not row.installation_id or not row.private_key_ref:
        row.status = "invalid"
        row.last_error = "GitHub App id, installation, and private key reference are required"
        row.last_error_class = "CONFIG"
        session.flush()
        return {"connected": False, "detail": row.last_error, "status": row.status}
    try:
        from app.secrets.factory import secret_backend

        secret_backend().get_metadata(row.private_key_ref)
        row.status = "connected"
        row.last_validated_at = utcnow()
        row.last_error = ""
        row.last_error_class = ""
        connected = True
        detail = "GitHub App configuration is present"
    except Exception as error:  # noqa: BLE001
        row.status = "degraded"
        row.last_error = str(error)[:500]
        row.last_error_class = error.__class__.__name__
        connected = False
        detail = row.last_error
    _audit(session, "GITHUB_INTEGRATION_VALIDATED", actor, row.organization or row.app_id, detail)
    session.flush()
    return {
        "connected": connected,
        "account": row.organization,
        "principal": f"app:{row.app_id}",
        "detail": detail,
        "status": row.status,
    }


def create_azure_devops_integration(session: Session, body: dict, actor: str) -> dict:
    from sqlalchemy import select

    from app.db.models import PipelineProviderRow

    organization = (body.get("organization") or "").strip()
    if not organization:
        raise PlatformStateError("Azure DevOps organization is required")
    now = utcnow()
    row = session.scalar(select(PipelineProviderRow).where(PipelineProviderRow.key == "azure-devops"))
    ref = _store_secret_ref(
        f"azure-devops/{organization}/auth",
        body.get("authSecret"),
        body.get("authRef") or (row.auth_ref if row else ""),
    )
    if row is None:
        row = PipelineProviderRow(
            id=new_id("ado"),
            key="azure-devops",
            name=body.get("name") or "Azure DevOps",
            organization=organization,
            project=body.get("project") or "",
            base_url=body.get("baseUrl") or "https://dev.azure.com",
            auth_ref=ref,
            enabled=bool(body.get("enabled", True)),
            status="configured" if ref else "pending",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
    else:
        row.organization = organization
        row.project = body.get("project") or row.project
        row.base_url = body.get("baseUrl") or row.base_url
        row.auth_ref = ref
        row.name = body.get("name") or row.name
        row.enabled = bool(body.get("enabled", True))
        row.status = "configured" if ref else row.status
        row.updated_at = now
    _audit(session, "AZURE_DEVOPS_INTEGRATION_CREATED", actor, organization)
    session.flush()
    return _azure_dump(row)


def update_azure_devops_integration(session: Session, integration_id: str, body: dict, actor: str) -> dict:
    from app.db.models import PipelineProviderRow

    row = session.get(PipelineProviderRow, integration_id)
    if row is None:
        raise PlatformNotFoundError("Azure DevOps integration not found")
    if body.get("name"):
        row.name = body["name"]
    if body.get("organization") is not None:
        row.organization = body["organization"]
    if body.get("project") is not None:
        row.project = body["project"]
    if body.get("baseUrl"):
        row.base_url = body["baseUrl"]
    if body.get("authSecret") or body.get("authRef"):
        row.auth_ref = _store_secret_ref(row.auth_ref or f"azure-devops/{row.organization}/auth", body.get("authSecret"), body.get("authRef") or row.auth_ref)
    if body.get("enabled") is not None:
        row.enabled = bool(body["enabled"])
        row.status = "configured" if row.enabled else "disabled"
    row.updated_at = utcnow()
    _audit(session, "AZURE_DEVOPS_INTEGRATION_UPDATED", actor, row.organization or row.name)
    session.flush()
    return _azure_dump(row)


def validate_azure_devops_integration(session: Session, integration_id: str, actor: str) -> dict:
    from app.db.models import PipelineProviderRow

    row = session.get(PipelineProviderRow, integration_id)
    if row is None:
        raise PlatformNotFoundError("Azure DevOps integration not found")
    if not row.organization or not row.auth_ref:
        row.status = "invalid"
        session.flush()
        return {"connected": False, "detail": "Organization and auth reference are required", "status": row.status}
    try:
        from app.secrets.factory import secret_backend

        secret_backend().get_metadata(row.auth_ref)
        row.status = "connected"
        row.last_error = ""
        connected = True
        detail = "Azure DevOps configuration is present"
    except Exception as error:  # noqa: BLE001
        row.status = "degraded"
        row.last_error = str(error)[:500]
        connected = False
        detail = row.last_error
    _audit(session, "AZURE_DEVOPS_INTEGRATION_VALIDATED", actor, row.organization or row.name, detail)
    session.flush()
    return {"connected": connected, "account": row.organization, "principal": row.project, "detail": detail, "status": row.status}


def _github_dump(row) -> dict:
    return {
        "id": row.id,
        "name": f"GitHub {row.organization or row.app_id}",
        "type": "github",
        "status": row.status,
        "scope": row.organization,
        "note": row.last_error or "GitHub App",
        "enabled": row.status != "disabled",
        "appId": row.app_id,
        "installationId": row.installation_id,
        "privateKeyRef": row.private_key_ref,
    }


def _azure_dump(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "type": "azure_devops",
        "status": row.status,
        "scope": row.organization,
        "note": row.project or "Azure DevOps",
        "enabled": row.enabled,
        "authRef": row.auth_ref,
    }
