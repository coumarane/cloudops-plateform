from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings, settings
from app.core.logging import get_logger
from app.providers.aws.errors import AwsAuthError, AwsPermissionError, classify_aws_error
from app.providers.aws.models import AwsConnectionConfig

logger = get_logger(__name__)

_RETRY_CONFIG = Config(
    retries={"max_attempts": 5, "mode": "standard"},
    connect_timeout=5,
    read_timeout=20,
)


def connection_config(cfg: Settings | None = None, override: AwsConnectionConfig | None = None) -> AwsConnectionConfig:
    if override is not None:
        return override
    active = cfg or settings
    return AwsConnectionConfig(
        cloud_region=active.aws_cloud_region,
        account_id=active.aws_account_id,
        role_arn=active.aws_role_arn,
        external_id=active.aws_external_id,
        session_name=active.aws_session_name,
        profile=active.aws_profile,
        config_secret_arn=active.aws_config_secret_arn,
        platform_region=active.aws_platform_region,
        environment=active.aws_environment,
        account_alias=active.aws_account_alias,
        cluster_environment_tag=active.aws_cluster_environment_tag,
    )


def _base_session(config: AwsConnectionConfig) -> boto3.Session:
    kwargs: dict[str, Any] = {"region_name": config.cloud_region}
    if config.profile:
        kwargs["profile_name"] = config.profile
    return boto3.Session(**kwargs)


def _load_secret_config(session: boto3.Session, secret_arn: str) -> dict[str, Any]:
    client = session.client("secretsmanager", config=_RETRY_CONFIG)
    try:
        payload = client.get_secret_value(SecretId=secret_arn)
    except ClientError as error:
        raise classify_aws_error(error) from error
    raw = payload.get("SecretString") or ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise AwsAuthError("AWS connection secret reference is not valid JSON") from error
    if not isinstance(parsed, dict):
        raise AwsAuthError("AWS connection secret reference must be a JSON object")
    return parsed


def _merge_secret_config(config: AwsConnectionConfig, secret: dict[str, Any]) -> AwsConnectionConfig:
    if any(key.lower() in {"aws_access_key_id", "access_key_id", "aws_secret_access_key"} for key in secret):
        logger.warning("AWS connection secret contains long-lived keys; they are used in-memory only and never persisted")
    return AwsConnectionConfig(
        cloud_region=secret.get("region") or secret.get("cloudRegion") or config.cloud_region,
        account_id=secret.get("accountId") or secret.get("account_id") or config.account_id,
        role_arn=secret.get("roleArn") or secret.get("role_arn") or config.role_arn,
        external_id=secret.get("externalId") or secret.get("external_id") or config.external_id,
        session_name=config.session_name,
        profile=config.profile,
        config_secret_arn=config.config_secret_arn,
        platform_region=config.platform_region,
        environment=config.environment,
        account_alias=secret.get("accountAlias") or config.account_alias,
        cluster_environment_tag=secret.get("clusterEnvironmentTag") or config.cluster_environment_tag,
        environment_id=config.environment_id,
    )


def _ephemeral_key_session(base: boto3.Session, secret: dict[str, Any], region: str) -> boto3.Session | None:
    access_key = secret.get("aws_access_key_id") or secret.get("accessKeyId")
    secret_key = secret.get("aws_secret_access_key") or secret.get("secretAccessKey")
    token = secret.get("aws_session_token") or secret.get("sessionToken")
    if not access_key or not secret_key:
        return None
    return boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=token,
        region_name=region,
    )


def assume_role_session(base: boto3.Session, config: AwsConnectionConfig) -> boto3.Session:
    if not config.role_arn:
        return base
    sts = base.client("sts", config=_RETRY_CONFIG)
    kwargs: dict[str, Any] = {
        "RoleArn": config.role_arn,
        "RoleSessionName": config.session_name,
        "DurationSeconds": 3600,
    }
    if config.external_id:
        kwargs["ExternalId"] = config.external_id
    try:
        response = sts.assume_role(**kwargs)
    except ClientError as error:
        mapped = classify_aws_error(error)
        if isinstance(mapped, AwsPermissionError):
            raise AwsPermissionError("Not permitted to assume the CloudOps AWS role") from error
        if isinstance(mapped, AwsAuthError):
            raise
        raise mapped from error
    credentials = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=config.cloud_region,
    )


def build_session(cfg: Settings | None = None, config: AwsConnectionConfig | None = None) -> boto3.Session:
    resolved = config or connection_config(cfg)
    try:
        session = _base_session(resolved)
        secret: dict[str, Any] = {}
        if resolved.config_secret_arn:
            secret = _load_secret_config(session, resolved.config_secret_arn)
            resolved = _merge_secret_config(resolved, secret)
            ephemeral = _ephemeral_key_session(session, secret, resolved.cloud_region)
            if ephemeral is not None:
                session = ephemeral
        session = assume_role_session(session, resolved)
        sts = session.client("sts", config=_RETRY_CONFIG)
        identity = sts.get_caller_identity()
        account = identity.get("Account")
        if resolved.account_id and account and account != resolved.account_id:
            raise AwsPermissionError("Assumed AWS identity is not the configured account")
        logger.info(
            "AWS session ready account=%s arn=%s region=%s",
            account,
            identity.get("Arn"),
            resolved.cloud_region,
        )
        return session
    except (AwsAuthError, AwsPermissionError):
        raise
    except Exception as error:
        raise classify_aws_error(error) from error


def client_config() -> Config:
    return _RETRY_CONFIG
