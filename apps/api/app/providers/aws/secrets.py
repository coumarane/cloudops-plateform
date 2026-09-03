from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import CloudAccountRow, CloudEnvironmentRow, ManagedProviderRow
from app.db.session import SessionLocal
from app.domain.enums import CLOUD_REGIONS, Environment
from app.domain.models import SecretRecord
from app.platform.bindings import account_binding, environments_for_account
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.errors import classify_aws_error

logger = get_logger(__name__)


def _iso(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _environment_for_account(account: CloudAccountRow, environments: tuple[str, ...]) -> Environment:
    if account.account_class == "Production":
        for code in ("DEV", "INT/TST", "UAT", "NPD", "PRD"):
            if code in environments:
                return code  # type: ignore[return-value]
        return "PRD"
    for code in ("DEV", "INT/TST", "UAT"):
        if code in environments:
            return code  # type: ignore[return-value]
    return "DEV"


def _pairs_from_secret_string(raw: str) -> list[tuple[str, str]]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [("plaintext", raw)]
    if isinstance(parsed, dict):
        return [(str(key), "" if value is None else str(value)) for key, value in parsed.items()]
    return [("plaintext", raw)]


def _secret_keys(client, secret_id: str) -> list[str]:
    """Return JSON object keys only. Secret values are discarded immediately."""
    payload = client.get_secret_value(SecretId=secret_id)
    raw = payload.get("SecretString") or ""
    payload.clear()
    pairs = _pairs_from_secret_string(raw)
    raw = ""
    return [name for name, _value in pairs if name != "plaintext" or len(pairs) == 1]


def reveal_aws_secret_pairs(secret_id: str) -> list[dict[str, str]]:
    """Return key/value pairs for one secret. Callers must not log the values."""
    session = SessionLocal()
    try:
        accounts = list(
            session.scalars(
                select(CloudAccountRow)
                .join(ManagedProviderRow, CloudAccountRow.managed_provider_id == ManagedProviderRow.id)
                .where(
                    CloudAccountRow.provider == "AWS",
                    CloudAccountRow.enabled.is_(True),
                    ManagedProviderRow.enabled.is_(True),
                )
            )
        )
        for account in accounts:
            environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
            env_codes = environments_for_account(account, environments)
            binding = account_binding(account, env_codes)
            factory = AwsClientFactory(config=binding.connection_config())
            for cloud_region in _cloud_regions(account, binding.cloud_region):
                try:
                    client = factory.client("secretsmanager", region_name=cloud_region)
                    payload = client.get_secret_value(SecretId=secret_id)
                    raw = payload.get("SecretString") or ""
                    payload.clear()
                    pairs = _pairs_from_secret_string(raw)
                    raw = ""
                    logger.info("Secret reveal requested name=%s account=%s", secret_id.rsplit(":", 1)[-1], account.alias)
                    return [{"name": name, "revealed": value} for name, value in pairs]
                except Exception as error:
                    mapped = classify_aws_error(error)
                    if "not found" in str(mapped).lower() or "ResourceNotFound" in str(error):
                        continue
                    logger.warning("Secret reveal failed region=%s detail=%s", cloud_region, mapped)
        raise LookupError("Secret was not found in configured AWS accounts")
    finally:
        session.close()


def _cloud_regions(account: CloudAccountRow, binding_region: str) -> list[str]:
    regions: list[str] = []
    for candidate in (account.cloud_region, binding_region):
        if candidate and candidate not in regions:
            regions.append(candidate)
    platform_default = CLOUD_REGIONS.get(f"AWS-{account.platform_region}")
    if platform_default and platform_default not in regions:
        regions.append(platform_default)
    return regions


def list_live_aws_secrets() -> list[SecretRecord]:
    session = SessionLocal()
    try:
        accounts = list(
            session.scalars(
                select(CloudAccountRow)
                .join(ManagedProviderRow, CloudAccountRow.managed_provider_id == ManagedProviderRow.id)
                .where(
                    CloudAccountRow.provider == "AWS",
                    CloudAccountRow.enabled.is_(True),
                    ManagedProviderRow.enabled.is_(True),
                )
                .order_by(CloudAccountRow.alias)
            )
        )
        items: list[SecretRecord] = []
        seen: set[str] = set()
        for account in accounts:
            environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
            env_codes = environments_for_account(account, environments)
            binding = account_binding(account, env_codes)
            environment = _environment_for_account(account, env_codes)
            region = account.platform_region if account.platform_region in {"AMER", "EMEA", "APAC"} else "EMEA"
            factory = AwsClientFactory(config=binding.connection_config())
            for cloud_region in _cloud_regions(account, binding.cloud_region):
                try:
                    client = factory.client("secretsmanager", region_name=cloud_region)
                    paginator = client.get_paginator("list_secrets")
                    for page in paginator.paginate():
                        for secret in page.get("SecretList", []):
                            arn = str(secret.get("ARN") or "")
                            name = str(secret.get("Name") or "")
                            if not name or arn in seen:
                                continue
                            seen.add(arn or name)
                            last_changed = secret.get("LastChangedDate")
                            description = str(secret.get("Description") or "") or None
                            kms_key = str(secret.get("KmsKeyId") or "") or None
                            keys: list[str] = []
                            try:
                                keys = _secret_keys(client, arn or name)
                            except Exception as error:
                                logger.warning(
                                    "AWS secret keys unavailable name=%s detail=%s",
                                    name,
                                    classify_aws_error(error),
                                )
                            items.append(
                                SecretRecord(
                                    id=arn or f"aws-sm-{account.alias}-{name}",
                                    name=name,
                                    namespace="AWS/SecretsManager",
                                    provider="AWS",
                                    region=region,  # type: ignore[arg-type]
                                    environment=environment,
                                    account=account.display_name or account.alias,
                                    status="OK",
                                    lastRotated=_iso(last_changed if isinstance(last_changed, datetime) else None),
                                    nextDue="—",
                                    lastValidated="—",
                                    credentialType="application",
                                    secretBackend="aws",
                                    fingerprint=None,
                                    updatedBy=None,
                                    lifecycleStatus="HEALTHY",
                                    source="live",
                                    keys=keys,
                                    arn=arn or None,
                                    description=description,
                                    kmsKeyId=kms_key or "aws/secretsmanager",
                                    cloudRegion=cloud_region,
                                )
                            )
                except Exception as error:
                    logger.warning(
                        "AWS Secrets Manager list failed account=%s region=%s detail=%s",
                        account.alias,
                        cloud_region,
                        classify_aws_error(error),
                    )
        return items
    finally:
        session.close()
