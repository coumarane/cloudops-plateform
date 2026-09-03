from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import Principal, principal_from_headers, require_bootstrap_admin
from app.providers.gcp.auth import get_caller_identity, save_service_account
from app.providers.gcp.errors import classify_gcp_error
from app.providers.gcp.models import GcpConnectionConfig

router = APIRouter()


class GcpCredentialsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    projectId: str = Field(..., min_length=4, max_length=128)
    credentialsJson: str = Field(..., min_length=20, max_length=200000)
    region: str | None = Field(default="europe-west1", max_length=64)


@router.post("/admin/gcp-credentials")
def configure_gcp_credentials(body: GcpCredentialsWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:update")
    path = save_service_account(project_id=body.projectId, credentials_json=body.credentialsJson)
    config = GcpConnectionConfig(
        cloud_region=body.region or "europe-west1",
        account_id=body.projectId,
        project_id=body.projectId,
        credentials_file=str(path),
        platform_region="EMEA",
        environment="DEV",
        account_alias="gcp",
    )
    try:
        identity = get_caller_identity(config)
        return {
            "configured": True,
            "valid": True,
            "account": identity.get("account", ""),
            "arn": identity.get("arn", ""),
            "principal": identity.get("principal", ""),
            "region": body.region or "europe-west1",
        }
    except Exception as error:
        return {
            "configured": True,
            "valid": False,
            "account": "",
            "arn": "",
            "principal": "",
            "region": body.region or "europe-west1",
            "error": str(classify_gcp_error(error)),
        }


@router.get("/admin/gcp-credentials/status")
def get_gcp_credentials_status(principal: Principal = Depends(principal_from_headers)) -> dict:
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
            "error": str(classify_gcp_error(error)),
        }
