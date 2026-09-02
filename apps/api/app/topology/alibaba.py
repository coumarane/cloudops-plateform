from __future__ import annotations

import os

from app.core.config import settings
from app.topology.models import AccountBinding, AwsTopology

PROVIDER = "Alibaba"
NONPROD_ENVIRONMENTS = ("DEV", "INT/TST", "UAT")
PROD_ENVIRONMENTS = ("NPD", "PRD")
DEFAULT_CLOUD_REGION = "cn-hangzhou"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _env(*names: str) -> str | None:
    for name in names:
        value = _clean(os.environ.get(name))
        if value:
            return value
    return None


def _account(class_key: str, account_class: str, environments: tuple[str, ...], readonly: bool) -> AccountBinding:
    alias = f"alibaba-china-{class_key.lower()}"
    prefix = f"CLOUDOPS_ALIBABA_{class_key}"
    account_id = _env(f"{prefix}_ACCOUNT_ID")
    role_arn = _env(f"{prefix}_ROLE_ARN")
    key_id_ref = f"{prefix}_ACCESS_KEY_ID"
    secret_ref = f"{prefix}_ACCESS_KEY_SECRET"
    if class_key == "NONPROD":
        account_id = account_id or _env("CLOUDOPS_ALIBABA_ACCOUNT_ID")
        role_arn = role_arn or _env("CLOUDOPS_ALIBABA_ROLE_ARN")
        if not _env(key_id_ref) and _env("CLOUDOPS_ALIBABA_ACCESS_KEY_ID"):
            key_id_ref = "CLOUDOPS_ALIBABA_ACCESS_KEY_ID"
        if not _env(secret_ref) and _env("CLOUDOPS_ALIBABA_ACCESS_KEY_SECRET"):
            secret_ref = "CLOUDOPS_ALIBABA_ACCESS_KEY_SECRET"
    cloud_region = _env("CLOUDOPS_ALIBABA_CLOUD_REGION") or DEFAULT_CLOUD_REGION
    return AccountBinding(
        id=alias,
        provider=PROVIDER,
        logical_region="China",
        cloud_region=cloud_region,
        alias=alias,
        account_id=account_id,
        role_arn=role_arn,
        external_id=None,
        account_class=account_class,
        readonly=readonly,
        environments=environments,
        session_name=f"cloudops-{alias}"[:32],
        cluster_environment_tag=settings.alibaba_cluster_environment_tag,
        profile=None,
        config_secret_arn=None,
        credential_ref=f"env:{secret_ref}",
        access_key_id_ref=key_id_ref,
        access_key_secret_ref=secret_ref,
    )


def load_alibaba_topology() -> AwsTopology:
    accounts = (
        _account("NONPROD", "Non-production", NONPROD_ENVIRONMENTS, False),
        _account("PROD", "Production", PROD_ENVIRONMENTS, True),
    )
    return AwsTopology(accounts=accounts, scan_concurrency=max(1, settings.alibaba_scan_concurrency))
