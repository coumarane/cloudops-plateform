from __future__ import annotations

import configparser
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import Principal, principal_from_headers, require_bootstrap_admin

router = APIRouter()

_AWS_CREDENTIALS_PATH = Path.home() / ".aws" / "credentials"
_AWS_CONFIG_PATH = Path.home() / ".aws" / "config"


class AwsCredentialsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accessKeyId: str = Field(..., min_length=16, max_length=128)
    secretAccessKey: str = Field(..., min_length=16, max_length=128)
    sessionToken: str | None = Field(default=None, max_length=2048)
    region: str | None = Field(default=None, max_length=32)
    profile: str = Field(default="default", max_length=64)


@router.post("/admin/aws-credentials")
def configure_aws_credentials(body: AwsCredentialsWrite, principal: Principal = Depends(principal_from_headers)) -> dict:
    """Write AWS credentials to ~/.aws/credentials and validate with STS."""
    require_bootstrap_admin(principal, "provider:update")

    profile = body.profile

    # Write credentials file
    creds = configparser.ConfigParser()
    if _AWS_CREDENTIALS_PATH.exists():
        creds.read(str(_AWS_CREDENTIALS_PATH))
    if not creds.has_section(profile) and profile != "DEFAULT":
        creds.add_section(profile)

    section = profile if profile != "DEFAULT" else creds.default_section
    creds.set(section, "aws_access_key_id", body.accessKeyId)
    creds.set(section, "aws_secret_access_key", body.secretAccessKey)
    if body.sessionToken:
        creds.set(section, "aws_session_token", body.sessionToken)
    elif creds.has_option(section, "aws_session_token"):
        creds.remove_option(section, "aws_session_token")

    _AWS_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_AWS_CREDENTIALS_PATH, "w") as fh:
        creds.write(fh)

    # Write region to config file if provided
    if body.region:
        config = configparser.ConfigParser()
        if _AWS_CONFIG_PATH.exists():
            config.read(str(_AWS_CONFIG_PATH))
        config_section = profile if profile == "default" else f"profile {profile}"
        if config_section == "default":
            config_section = config.default_section
        else:
            if not config.has_section(config_section):
                config.add_section(config_section)
        config.set(config_section, "region", body.region)
        with open(_AWS_CONFIG_PATH, "w") as fh:
            config.write(fh)

    # Validate credentials with STS
    try:
        session = boto3.Session(
            aws_access_key_id=body.accessKeyId,
            aws_secret_access_key=body.secretAccessKey,
            aws_session_token=body.sessionToken,
            region_name=body.region or "us-east-1",
        )
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return {
            "configured": True,
            "valid": True,
            "account": identity.get("Account", ""),
            "arn": identity.get("Arn", ""),
            "principal": (identity.get("Arn", "").rsplit("/", 1)[-1]) if identity.get("Arn") else "",
            "region": body.region or "us-east-1",
            "profile": profile,
        }
    except (ClientError, NoCredentialsError) as exc:
        return {
            "configured": True,
            "valid": False,
            "account": "",
            "arn": "",
            "principal": "",
            "region": body.region or "us-east-1",
            "profile": profile,
            "error": str(exc),
        }


@router.get("/admin/aws-credentials/status")
def get_aws_credentials_status(principal: Principal = Depends(principal_from_headers)) -> dict:
    """Check current AWS credentials status without exposing secret values."""
    require_bootstrap_admin(principal, "provider:read")

    has_credentials = _AWS_CREDENTIALS_PATH.exists()
    profile_names: list[str] = []
    if has_credentials:
        creds = configparser.ConfigParser()
        creds.read(str(_AWS_CREDENTIALS_PATH))
        profile_names = ["default"] if creds.defaults() else []
        profile_names += creds.sections()

    # Check if credentials are valid
    try:
        session = boto3.Session()
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return {
            "configured": True,
            "valid": True,
            "profiles": profile_names,
            "account": identity.get("Account", ""),
            "arn": identity.get("Arn", ""),
            "principal": (identity.get("Arn", "").rsplit("/", 1)[-1]) if identity.get("Arn") else "",
        }
    except Exception as exc:
        return {
            "configured": has_credentials,
            "valid": False,
            "profiles": profile_names,
            "account": "",
            "arn": "",
            "principal": "",
            "error": str(exc),
        }
