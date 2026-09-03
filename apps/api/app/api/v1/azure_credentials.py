from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import Principal, principal_from_headers, require_bootstrap_admin
from app.providers.azure.auth import get_caller_identity, save_service_principal
from app.providers.azure.errors import classify_azure_error
from app.providers.azure.models import AzureConnectionConfig

router = APIRouter()


class AzureCredentialsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenantId: str = Field(..., min_length=8, max_length=128)
    clientId: str = Field(..., min_length=8, max_length=128)
    clientSecret: str = Field(..., min_length=8, max_length=256)
    subscriptionId: str | None = Field(default=None, max_length=128)
    vaultUrl: str | None = Field(default=None, max_length=512)
    region: str | None = Field(default="westeurope", max_length=64)


@router.post("/admin/azure-credentials")
def configure_azure_credentials(body: AzureCredentialsWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:update")
    save_service_principal(
        tenant_id=body.tenantId,
        client_id=body.clientId,
        client_secret=body.clientSecret,
        subscription_id=body.subscriptionId or "",
        vault_url=body.vaultUrl or "",
    )
    config = AzureConnectionConfig(
        cloud_region=body.region or "westeurope",
        account_id=body.subscriptionId,
        tenant_id=body.tenantId,
        client_id=body.clientId,
        client_secret_ref=None,
        vault_url=body.vaultUrl,
        platform_region="EMEA",
        environment="DEV",
        account_alias="azure",
    )
    try:
        identity = get_caller_identity(config)
        return {
            "configured": True,
            "valid": True,
            "account": identity.get("account", ""),
            "arn": identity.get("arn", ""),
            "principal": identity.get("principal", ""),
            "region": body.region or "westeurope",
        }
    except Exception as error:
        return {
            "configured": True,
            "valid": False,
            "account": "",
            "arn": "",
            "principal": "",
            "region": body.region or "westeurope",
            "error": str(classify_azure_error(error)),
        }


@router.get("/admin/azure-credentials/status")
def get_azure_credentials_status(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:read")
    try:
        identity = get_caller_identity()
        return {
            "configured": True,
            "valid": True,
            "account": identity.get("account", ""),
            "arn": identity.get("arn", ""),
            "principal": identity.get("principal", ""),
        }
    except Exception as error:
        return {
            "configured": False,
            "valid": False,
            "account": "",
            "arn": "",
            "principal": "",
            "error": str(classify_azure_error(error)),
        }
