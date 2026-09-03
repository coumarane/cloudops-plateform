from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import CloudAccountRow, CloudEnvironmentRow, ManagedProviderRow
from app.db.session import SessionLocal
from app.domain.enums import Environment
from app.domain.models import SecretRecord
from app.platform.bindings import account_binding, environments_for_account
from app.providers.azure.auth import load_service_principal
from app.providers.azure.client import AzureClientFactory
from app.providers.azure.errors import classify_azure_error
from app.providers.azure.models import AzureConnectionConfig

logger = get_logger(__name__)


def _iso(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _environment_for_account(account: CloudAccountRow, environments: tuple[str, ...]) -> Environment:
    for code in ("DEV", "INT/TST", "UAT", "NPD", "PRD"):
        if code in environments:
            return code  # type: ignore[return-value]
    return "DEV"


def _pairs_from_secret_string(raw: str) -> list[tuple[str, str]]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [("value", raw)]
    if isinstance(parsed, dict):
        return [(str(key), "" if value is None else str(value)) for key, value in parsed.items()]
    return [("value", raw)]


def _azure_accounts(session):
    return list(
        session.scalars(
            select(CloudAccountRow)
            .join(ManagedProviderRow, CloudAccountRow.managed_provider_id == ManagedProviderRow.id)
            .where(
                CloudAccountRow.provider == "Azure",
                CloudAccountRow.enabled.is_(True),
                ManagedProviderRow.enabled.is_(True),
            )
            .order_by(CloudAccountRow.alias)
        )
    )


def _config_for(account: CloudAccountRow, environments: tuple[str, ...]) -> AzureConnectionConfig:
    stored = load_service_principal()
    binding = account_binding(account, environments)
    return AzureConnectionConfig(
        cloud_region=binding.cloud_region or "westeurope",
        account_id=account.account_id or stored.get("subscriptionId") or None,
        tenant_id=stored.get("tenantId") or None,
        client_id=stored.get("clientId") or None,
        client_secret_ref=None,
        vault_url=stored.get("vaultUrl") or None,
        platform_region=account.platform_region or "EMEA",
        environment=environments[0] if environments else "DEV",
        account_alias=account.alias,
        credential_ref=account.credential_ref or None,
    )


def list_live_azure_secrets() -> list[SecretRecord]:
    session = SessionLocal()
    try:
        items: list[SecretRecord] = []
        seen: set[str] = set()
        accounts = _azure_accounts(session)
        if not accounts:
            # Still allow vault configured via Cloud Credentials without a DB account.
            stored = load_service_principal()
            if not stored.get("vaultUrl"):
                return []
            accounts = []
        configs: list[tuple[str, str, Environment, AzureConnectionConfig]] = []
        if accounts:
            for account in accounts:
                environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
                env_codes = environments_for_account(account, environments)
                configs.append(
                    (
                        account.display_name or account.alias,
                        account.platform_region if account.platform_region in {"AMER", "EMEA", "APAC"} else "EMEA",
                        _environment_for_account(account, env_codes),
                        _config_for(account, env_codes),
                    )
                )
        else:
            stored = load_service_principal()
            configs.append(
                (
                    "Azure",
                    "EMEA",
                    "DEV",
                    AzureConnectionConfig(
                        cloud_region="westeurope",
                        account_id=stored.get("subscriptionId") or None,
                        tenant_id=stored.get("tenantId") or None,
                        client_id=stored.get("clientId") or None,
                        client_secret_ref=None,
                        vault_url=stored.get("vaultUrl") or None,
                        platform_region="EMEA",
                        environment="DEV",
                        account_alias="azure",
                    ),
                )
            )
        for account_name, region, environment, config in configs:
            try:
                client = AzureClientFactory(config).secret_client()
                for props in client.list_properties_of_secrets():
                    name = str(getattr(props, "name", "") or "")
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    keys: list[str] = []
                    try:
                        secret = client.get_secret(name)
                        keys = [key for key, _ in _pairs_from_secret_string(str(secret.value or ""))]
                    except Exception as error:
                        logger.warning("Azure secret keys unavailable name=%s detail=%s", name, classify_azure_error(error))
                    items.append(
                        SecretRecord(
                            id=f"azure-kv-{account_name}-{name}",
                            name=name,
                            namespace="Azure/KeyVault",
                            provider="Azure",
                            region=region,  # type: ignore[arg-type]
                            environment=environment,
                            account=account_name,
                            status="OK",
                            lastRotated=_iso(getattr(props, "updated_on", None)),
                            nextDue="—",
                            lastValidated="—",
                            credentialType="application",
                            secretBackend="azure",
                            lifecycleStatus="HEALTHY",
                            source="live",
                            keys=[key for key in keys if key != "value" or len(keys) == 1],
                            arn=name,
                            description=getattr(props, "content_type", None),
                            cloudRegion=config.cloud_region,
                        )
                    )
            except Exception as error:
                logger.warning("Azure Key Vault list failed account=%s detail=%s", account_name, classify_azure_error(error))
        return items
    finally:
        session.close()


def reveal_azure_secret_pairs(secret_id: str) -> list[dict[str, str]]:
    names = [secret_id]
    if secret_id.startswith("azure-kv-"):
        names.append(secret_id.rsplit("-", 1)[-1])
        names.append(secret_id[len("azure-kv-") :])
    session = SessionLocal()
    try:
        accounts = _azure_accounts(session)
        configs: list[AzureConnectionConfig] = []
        if accounts:
            for account in accounts:
                environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
                configs.append(_config_for(account, environments_for_account(account, environments)))
        else:
            stored = load_service_principal()
            configs.append(
                AzureConnectionConfig(
                    cloud_region="westeurope",
                    account_id=stored.get("subscriptionId") or None,
                    tenant_id=stored.get("tenantId") or None,
                    client_id=stored.get("clientId") or None,
                    client_secret_ref=None,
                    vault_url=stored.get("vaultUrl") or None,
                    platform_region="EMEA",
                    environment="DEV",
                    account_alias="azure",
                )
            )
        for config in configs:
            try:
                client = AzureClientFactory(config).secret_client()
                for name in names:
                    try:
                        secret = client.get_secret(name)
                        pairs = _pairs_from_secret_string(str(secret.value or ""))
                        if pairs:
                            logger.info("Azure secret reveal requested name=%s", name)
                            return [{"name": key, "revealed": value} for key, value in pairs]
                    except Exception:
                        continue
            except Exception as error:
                logger.warning("Azure secret reveal skipped detail=%s", classify_azure_error(error))
        raise LookupError("Secret was not found in configured Azure Key Vaults")
    finally:
        session.close()
