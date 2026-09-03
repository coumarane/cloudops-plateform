from __future__ import annotations

import configparser
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import Principal, principal_from_headers, require_bootstrap_admin
from app.providers.alibaba.auth import get_caller_identity
from app.providers.alibaba.exceptions import classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig

router = APIRouter()

_ALIYUN_CREDENTIALS_PATH = Path.home() / ".aliyun" / "credentials"


class AlibabaCredentialsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accessKeyId: str = Field(..., min_length=8, max_length=128)
    accessKeySecret: str = Field(..., min_length=8, max_length=128)
    region: str | None = Field(default="cn-hangzhou", max_length=32)


@router.post("/admin/alibaba-credentials")
def configure_alibaba_credentials(body: AlibabaCredentialsWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:update")
    creds = configparser.ConfigParser()
    if _ALIYUN_CREDENTIALS_PATH.exists():
        creds.read(str(_ALIYUN_CREDENTIALS_PATH))
    if not creds.has_section("default"):
        creds.add_section("default")
    creds.set("default", "access_key_id", body.accessKeyId)
    creds.set("default", "access_key_secret", body.accessKeySecret)
    creds.set("default", "region_id", body.region or "cn-hangzhou")
    _ALIYUN_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_ALIYUN_CREDENTIALS_PATH, "w") as fh:
        creds.write(fh)
    config = AlibabaConnectionConfig(
        cloud_region=body.region or "cn-hangzhou",
        account_id=None,
        role_arn=None,
        session_name="cloudops-admin",
        access_key_id_ref=None,
        access_key_secret_ref=None,
        credential_ref=None,
        platform_region="China",
        environment="DEV",
        account_alias="alibaba-china-nonprod",
        cluster_environment_tag="Environment",
    )
    try:
        identity = get_caller_identity(config)
        return {
            "configured": True,
            "valid": True,
            "account": identity.account_id,
            "arn": identity.arn,
            "principal": identity.arn.rsplit("/", 1)[-1] if identity.arn else "",
            "region": body.region or "cn-hangzhou",
        }
    except Exception as error:
        return {
            "configured": True,
            "valid": False,
            "account": "",
            "arn": "",
            "principal": "",
            "region": body.region or "cn-hangzhou",
            "error": str(classify_alibaba_error(error)),
        }


@router.get("/admin/alibaba-credentials/status")
def get_alibaba_credentials_status(principal: Principal = Depends(principal_from_headers)) -> dict:
    require_bootstrap_admin(principal, "provider:read")
    configured = _ALIYUN_CREDENTIALS_PATH.exists()
    config = AlibabaConnectionConfig(
        cloud_region="cn-hangzhou",
        account_id=None,
        role_arn=None,
        session_name="cloudops-admin",
        access_key_id_ref=None,
        access_key_secret_ref=None,
        credential_ref=None,
        platform_region="China",
        environment="DEV",
        account_alias="alibaba-china-nonprod",
        cluster_environment_tag="Environment",
    )
    try:
        identity = get_caller_identity(config)
        return {
            "configured": True,
            "valid": True,
            "account": identity.account_id,
            "arn": identity.arn,
            "principal": identity.arn.rsplit("/", 1)[-1] if identity.arn else "",
        }
    except Exception as error:
        return {
            "configured": configured,
            "valid": False,
            "account": "",
            "arn": "",
            "principal": "",
            "error": str(classify_alibaba_error(error)),
        }
