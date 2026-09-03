from __future__ import annotations

import hashlib
import os
from typing import Any

from app.core.logging import get_logger
from app.providers.alibaba.exceptions import AlibabaAuthError, AlibabaPermissionError, classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig, AlibabaIdentity

logger = get_logger(__name__)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def resolve_secret(ref: str | None) -> str | None:
    """Resolve a credential reference. Only env:NAME and bare env var names are supported."""
    if not ref:
        return None
    name = ref[4:] if ref.startswith("env:") else ref
    return _clean(os.environ.get(name))


def fingerprint_access_key_id(access_key_id: str) -> str:
    return hashlib.sha256(access_key_id.encode("utf-8")).hexdigest()[:16]


def load_static_keys(config: AlibabaConnectionConfig) -> tuple[str, str]:
    access_key_id = resolve_secret(config.access_key_id_ref)
    access_key_secret = resolve_secret(config.access_key_secret_ref)
    if not access_key_id:
        access_key_id = _clean(os.environ.get("CLOUDOPS_ALIBABA_ACCESS_KEY_ID") or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID"))
    if not access_key_secret:
        access_key_secret = _clean(
            os.environ.get("CLOUDOPS_ALIBABA_ACCESS_KEY_SECRET") or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        )
    if not access_key_id or not access_key_secret:
        access_key_id, access_key_secret = _keys_from_aliyun_file()
    if not access_key_id or not access_key_secret:
        raise AlibabaAuthError("Alibaba credentials were not found or were incomplete")
    return access_key_id, access_key_secret


def _keys_from_aliyun_file() -> tuple[str | None, str | None]:
    from pathlib import Path
    import configparser

    path = Path.home() / ".aliyun" / "credentials"
    if not path.exists():
        return None, None
    parser = configparser.ConfigParser()
    parser.read(str(path))
    section = "default" if parser.has_section("default") else parser.default_section
    try:
        key_id = _clean(parser.get(section, "access_key_id", fallback="") or parser.get(section, "accessKeyId", fallback=""))
        key_secret = _clean(
            parser.get(section, "access_key_secret", fallback="") or parser.get(section, "accessKeySecret", fallback="")
        )
    except Exception:
        return None, None
    return key_id, key_secret


def _openapi_config(access_key_id: str, access_key_secret: str, region: str, endpoint: str, token: str | None = None):
    from alibabacloud_tea_openapi import models as open_api_models

    kwargs: dict[str, Any] = {
        "access_key_id": access_key_id,
        "access_key_secret": access_key_secret,
        "region_id": region,
        "endpoint": endpoint,
    }
    if token:
        kwargs["security_token"] = token
    return open_api_models.Config(**kwargs)


def assume_role(config: AlibabaConnectionConfig, access_key_id: str, access_key_secret: str) -> tuple[str, str, str]:
    if not config.role_arn:
        return access_key_id, access_key_secret, ""
    try:
        from alibabacloud_sts20150401.client import Client as StsClient
        from alibabacloud_sts20150401 import models as sts_models
    except ImportError as error:
        raise AlibabaAuthError("Alibaba STS SDK is not installed") from error
    client = StsClient(_openapi_config(access_key_id, access_key_secret, config.cloud_region, "sts.aliyuncs.com"))
    request = sts_models.AssumeRoleRequest(
        role_arn=config.role_arn,
        role_session_name=config.session_name[:32] or "cloudops",
        duration_seconds=3600,
    )
    try:
        response = client.assume_role(request)
    except Exception as error:
        mapped = classify_alibaba_error(error)
        if isinstance(mapped, AlibabaPermissionError):
            raise AlibabaPermissionError("Not permitted to assume the CloudOps Alibaba RAM role") from error
        raise mapped from error
    credentials = response.body.credentials
    return credentials.access_key_id, credentials.access_key_secret, credentials.security_token or ""


def get_caller_identity(config: AlibabaConnectionConfig) -> AlibabaIdentity:
    access_key_id, access_key_secret = load_static_keys(config)
    access_key_id, access_key_secret, token = assume_role(config, access_key_id, access_key_secret)
    try:
        from alibabacloud_sts20150401.client import Client as StsClient
        from alibabacloud_sts20150401 import models as sts_models
    except ImportError as error:
        raise AlibabaAuthError("Alibaba STS SDK is not installed") from error
    client = StsClient(
        _openapi_config(access_key_id, access_key_secret, config.cloud_region, "sts.aliyuncs.com", token or None)
    )
    try:
        response = client.get_caller_identity()
    except Exception as error:
        raise classify_alibaba_error(error) from error
    body = response.body
    account = str(body.account_id or "")
    if config.account_id and account and account != config.account_id:
        raise AlibabaPermissionError("Assumed Alibaba identity is not the configured account")
    fingerprint = fingerprint_access_key_id(resolve_secret(config.access_key_id_ref) or account)
    logger.info("Alibaba session ready account=%s arn=%s region=%s", account, body.arn, config.cloud_region)
    return AlibabaIdentity(account_id=account, arn=str(body.arn or ""), fingerprint=fingerprint, status="ok")
