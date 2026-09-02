from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import settings
from app.topology.models import AccountBinding, AwsTopology

PROVIDER = "AWS"
NONPROD_ENVIRONMENTS = ("DEV", "INT/TST", "UAT")
PROD_ENVIRONMENTS = ("NPD", "PRD")

DEFAULT_REGIONS: tuple[tuple[str, str], ...] = (
    ("AMER", "us-east-1"),
    ("EMEA", "eu-west-1"),
    ("APAC", "ap-southeast-1"),
)


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


def _region_cloud(logical_region: str, default_cloud: str) -> str:
    override = _env(f"CLOUDOPS_AWS_{logical_region}_CLOUD_REGION")
    return override or default_cloud


def _account_credentials(logical_region: str, class_key: str) -> tuple[str | None, str | None, str | None]:
    prefix = f"CLOUDOPS_AWS_{logical_region}_{class_key}"
    account_id = _env(f"{prefix}_ACCOUNT_ID")
    role_arn = _env(f"{prefix}_ROLE_ARN")
    external_id = _env(f"{prefix}_EXTERNAL_ID", "CLOUDOPS_AWS_EXTERNAL_ID")
    if logical_region == "EMEA" and class_key == "NONPROD":
        account_id = account_id or _env("CLOUDOPS_AWS_ACCOUNT_ID")
        role_arn = role_arn or _env("CLOUDOPS_AWS_ROLE_ARN")
    return account_id, role_arn, external_id


def _account(
    logical_region: str,
    cloud_region: str,
    class_key: str,
    account_class: str,
    environments: tuple[str, ...],
    readonly: bool,
) -> AccountBinding:
    alias = f"aws-{logical_region.lower()}-{class_key.lower()}"
    account_id, role_arn, external_id = _account_credentials(logical_region, class_key)
    return AccountBinding(
        id=alias,
        provider=PROVIDER,
        logical_region=logical_region,
        cloud_region=cloud_region,
        alias=alias,
        account_id=account_id,
        role_arn=role_arn,
        external_id=external_id,
        account_class=account_class,
        readonly=readonly,
        environments=environments,
        session_name=f"cloudops-{alias}",
        cluster_environment_tag=settings.aws_cluster_environment_tag,
        profile=settings.aws_profile,
        config_secret_arn=settings.aws_config_secret_arn,
    )


def _default_accounts() -> tuple[AccountBinding, ...]:
    accounts: list[AccountBinding] = []
    for logical_region, default_cloud in DEFAULT_REGIONS:
        cloud_region = _region_cloud(logical_region, default_cloud)
        accounts.append(
            _account(logical_region, cloud_region, "NONPROD", "Non-production", NONPROD_ENVIRONMENTS, False)
        )
        accounts.append(_account(logical_region, cloud_region, "PROD", "Production", PROD_ENVIRONMENTS, True))
    return tuple(accounts)


def _from_json(path: Path) -> AwsTopology:
    payload = json.loads(path.read_text())
    concurrency = int(payload.get("concurrency") or settings.aws_scan_concurrency)
    tag = payload.get("clusterEnvironmentTag") or settings.aws_cluster_environment_tag
    profile = payload.get("profile") or settings.aws_profile
    secret = payload.get("configSecretArn") or settings.aws_config_secret_arn
    shared_external = payload.get("externalId") or settings.aws_external_id
    accounts: list[AccountBinding] = []
    for region in payload.get("regions") or []:
        logical_region = region["id"]
        cloud_region = region.get("cloudRegion") or _region_cloud(logical_region, "")
        for account in region.get("accounts") or []:
            alias = account["alias"]
            environments = tuple(account.get("environments") or ())
            account_class = account.get("accountClass") or "Non-production"
            readonly = bool(account.get("readonly", account_class == "Production"))
            accounts.append(
                AccountBinding(
                    id=alias,
                    provider=PROVIDER,
                    logical_region=logical_region,
                    cloud_region=cloud_region,
                    alias=alias,
                    account_id=_clean(account.get("accountId")),
                    role_arn=_clean(account.get("roleArn")),
                    external_id=_clean(account.get("externalId")) or _clean(shared_external),
                    account_class=account_class,
                    readonly=readonly,
                    environments=environments,
                    session_name=account.get("sessionName") or f"cloudops-{alias}",
                    cluster_environment_tag=account.get("clusterEnvironmentTag") or tag,
                    profile=_clean(account.get("profile")) or profile,
                    config_secret_arn=_clean(account.get("configSecretArn")) or secret,
                )
            )
    return AwsTopology(accounts=tuple(accounts), scan_concurrency=max(1, concurrency))


def load_topology() -> AwsTopology:
    path = _clean(settings.aws_topology_path)
    if path:
        return _from_json(Path(path))
    return AwsTopology(accounts=_default_accounts(), scan_concurrency=max(1, settings.aws_scan_concurrency))
