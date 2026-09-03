from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.logging import get_logger
from app.providers.azure.errors import AzureAuthError, classify_azure_error
from app.providers.azure.models import AzureConnectionConfig

logger = get_logger(__name__)

_AZURE_PROFILE = Path.home() / ".azure" / "cloudops.json"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def load_service_principal() -> dict[str, str]:
    if _AZURE_PROFILE.exists():
        try:
            payload = json.loads(_AZURE_PROFILE.read_text())
            if isinstance(payload, dict):
                return {
                    "tenantId": str(payload.get("tenantId") or ""),
                    "clientId": str(payload.get("clientId") or ""),
                    "clientSecret": str(payload.get("clientSecret") or ""),
                    "subscriptionId": str(payload.get("subscriptionId") or ""),
                    "vaultUrl": str(payload.get("vaultUrl") or ""),
                }
        except Exception:
            pass
    return {
        "tenantId": os.environ.get("AZURE_TENANT_ID") or os.environ.get("CLOUDOPS_AZURE_TENANT_ID") or "",
        "clientId": os.environ.get("AZURE_CLIENT_ID") or os.environ.get("CLOUDOPS_AZURE_CLIENT_ID") or "",
        "clientSecret": os.environ.get("AZURE_CLIENT_SECRET") or os.environ.get("CLOUDOPS_AZURE_CLIENT_SECRET") or "",
        "subscriptionId": os.environ.get("AZURE_SUBSCRIPTION_ID") or os.environ.get("CLOUDOPS_AZURE_SUBSCRIPTION_ID") or "",
        "vaultUrl": os.environ.get("AZURE_KEY_VAULT_URL") or os.environ.get("CLOUDOPS_AZURE_KEY_VAULT_URL") or "",
    }


def save_service_principal(*, tenant_id: str, client_id: str, client_secret: str, subscription_id: str = "", vault_url: str = "") -> None:
    _AZURE_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tenantId": tenant_id,
        "clientId": client_id,
        "clientSecret": client_secret,
        "subscriptionId": subscription_id,
        "vaultUrl": vault_url,
    }
    _AZURE_PROFILE.write_text(json.dumps(payload, indent=2))


def credential_from_config(config: AzureConnectionConfig | None = None):
    try:
        from azure.identity import ClientSecretCredential, DefaultAzureCredential
    except ImportError as error:
        raise AzureAuthError("Azure Identity SDK is not installed") from error

    stored = load_service_principal()
    tenant_id = _clean(config.tenant_id if config else None) or _clean(stored.get("tenantId"))
    client_id = _clean(config.client_id if config else None) or _clean(stored.get("clientId"))
    client_secret = _clean(stored.get("clientSecret"))
    if tenant_id and client_id and client_secret:
        return ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


def get_caller_identity(config: AzureConnectionConfig | None = None) -> dict[str, str]:
    stored = load_service_principal()
    subscription_id = _clean(config.account_id if config else None) or _clean(stored.get("subscriptionId"))
    try:
        from azure.mgmt.subscription import SubscriptionClient
    except ImportError:
        # Fall back to validating credential acquisition only.
        credential_from_config(config)
        return {
            "account": subscription_id or "",
            "arn": f"azure://tenant/{stored.get('tenantId') or 'unknown'}/client/{stored.get('clientId') or 'default'}",
            "principal": stored.get("clientId") or "DefaultAzureCredential",
        }
    try:
        client = SubscriptionClient(credential_from_config(config))
        if subscription_id:
            sub = client.subscriptions.get(subscription_id)
            return {
                "account": subscription_id,
                "arn": f"azure://subscriptions/{subscription_id}",
                "principal": getattr(sub, "display_name", None) or subscription_id,
            }
        items = list(client.subscriptions.list())
        if not items:
            raise AzureAuthError("Azure credentials are valid but no subscriptions are visible")
        first = items[0]
        return {
            "account": str(getattr(first, "subscription_id", "") or ""),
            "arn": f"azure://subscriptions/{getattr(first, 'subscription_id', '')}",
            "principal": str(getattr(first, "display_name", "") or getattr(first, "subscription_id", "")),
        }
    except Exception as error:
        raise classify_azure_error(error) from error
