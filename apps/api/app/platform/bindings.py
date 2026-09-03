from __future__ import annotations

import json

from app.db.models import CloudAccountRow, CloudEnvironmentRow
from app.topology.models import AccountBinding, environment_scope_id


def environments_for_account(account: CloudAccountRow, rows: list[CloudEnvironmentRow]) -> tuple[str, ...]:
    return tuple(item.environment for item in rows if item.account_id == account.id and item.enabled)


def account_binding(account: CloudAccountRow, environments: tuple[str, ...]) -> AccountBinding:
    extra: dict = {}
    try:
        extra = json.loads(account.cloud_regions_json or "[]")
    except Exception:
        extra = []
    cloud_region = account.cloud_region
    if isinstance(extra, list) and extra and isinstance(extra[0], str):
        cloud_region = extra[0] or cloud_region
    return AccountBinding(
        id=account.id,
        provider=account.provider,
        logical_region=account.platform_region,
        cloud_region=cloud_region,
        alias=account.alias,
        account_id=account.account_id or None,
        role_arn=account.role_arn or account.ram_role or None,
        external_id=account.external_id or None,
        account_class=account.account_class,
        readonly=account.readonly,
        environments=environments or ("DEV",),
        session_name=account.session_name or "cloudops-admin",
        cluster_environment_tag=account.cluster_environment_tag or "Environment",
        profile=None,
        config_secret_arn=account.credential_ref if (account.credential_ref or "").startswith("arn:") else None,
        credential_ref=account.credential_ref or None,
        access_key_id_ref=None,
        access_key_secret_ref=account.credential_ref if account.provider == "Alibaba" else None,
    )


def ensure_environment_id(account: CloudAccountRow, environment: str) -> str:
    return environment_scope_id(account.alias, environment)
