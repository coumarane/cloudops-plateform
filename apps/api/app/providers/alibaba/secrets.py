from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import CloudAccountRow, CloudEnvironmentRow, ManagedProviderRow
from app.db.session import SessionLocal
from app.domain.enums import Environment
from app.domain.models import SecretRecord
from app.platform.bindings import account_binding, environments_for_account
from app.providers.alibaba.client import AlibabaClientFactory
from app.providers.alibaba.exceptions import classify_alibaba_error

logger = get_logger(__name__)


def _iso(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _environment_for_account(account: CloudAccountRow, environments: tuple[str, ...]) -> Environment:
    if account.account_class == "Production":
        for code in ("DEV", "TST", "UAT", "NPD", "PRD"):
            if code in environments:
                return "DEV" if code == "TST" else code  # type: ignore[return-value]
        return "PRD"
    for code in ("DEV", "INT/TST", "UAT"):
        if code in environments:
            return code  # type: ignore[return-value]
    return "DEV"


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_map"):
        return value.to_map() or {}
    return {}


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


def _secret_data(client, secret_name: str) -> str:
    from alibabacloud_kms20160120 import models as kms_models

    response = client.get_secret_value(kms_models.GetSecretValueRequest(secret_name=secret_name))
    body = _as_dict(getattr(response, "body", response))
    return str(body.get("SecretData") or body.get("secret_data") or body.get("secretData") or "")


def _enabled_alibaba_accounts(session):
    return list(
        session.scalars(
            select(CloudAccountRow)
            .join(ManagedProviderRow, CloudAccountRow.managed_provider_id == ManagedProviderRow.id)
            .where(
                CloudAccountRow.provider == "Alibaba",
                CloudAccountRow.enabled.is_(True),
                ManagedProviderRow.enabled.is_(True),
            )
            .order_by(CloudAccountRow.alias)
        )
    )


def list_live_alibaba_secrets() -> list[SecretRecord]:
    session = SessionLocal()
    try:
        items: list[SecretRecord] = []
        seen: set[str] = set()
        for account in _enabled_alibaba_accounts(session):
            environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
            env_codes = environments_for_account(account, environments)
            binding = account_binding(account, env_codes)
            environment = _environment_for_account(account, env_codes)
            factory = AlibabaClientFactory(binding.connection_config())
            try:
                client = factory.kms_client()
                from alibabacloud_kms20160120 import models as kms_models

                page = 1
                while True:
                    response = client.list_secrets(kms_models.ListSecretsRequest(page_number=page, page_size=100))
                    body = _as_dict(getattr(response, "body", response))
                    rows = (
                        body.get("SecretList")
                        or body.get("secret_list")
                        or body.get("secretList")
                        or {}
                    )
                    if isinstance(rows, dict):
                        rows = rows.get("Secret") or rows.get("secret") or []
                    if not isinstance(rows, list):
                        rows = []
                    for secret in rows:
                        payload = _as_dict(secret)
                        name = str(payload.get("SecretName") or payload.get("secret_name") or payload.get("secretName") or "")
                        if not name or name in seen:
                            continue
                        seen.add(name)
                        keys: list[str] = []
                        try:
                            raw = _secret_data(client, name)
                            keys = [key for key, _value in _pairs_from_secret_string(raw)]
                            raw = ""
                        except Exception as error:
                            logger.warning("Alibaba secret keys unavailable name=%s detail=%s", name, classify_alibaba_error(error))
                        items.append(
                            SecretRecord(
                                id=f"aliyun-kms-{account.alias}-{name}",
                                name=name,
                                namespace="Alibaba/KMS",
                                provider="Alibaba",
                                region="China",
                                environment=environment,
                                account=account.display_name or account.alias,
                                status="OK",
                                lastRotated=_iso(payload.get("UpdateTime") or payload.get("update_time")),
                                nextDue="—",
                                lastValidated="—",
                                credentialType="application",
                                secretBackend="alibaba",
                                fingerprint=None,
                                updatedBy=None,
                                lifecycleStatus="HEALTHY",
                                source="live",
                                keys=[key for key in keys if key != "plaintext" or len(keys) == 1],
                                arn=name,
                                description=str(payload.get("Description") or payload.get("description") or "") or None,
                                kmsKeyId=str(payload.get("EncryptionKeyId") or payload.get("encryption_key_id") or "") or None,
                                cloudRegion=account.cloud_region or "cn-hangzhou",
                            )
                        )
                    total = int(body.get("TotalCount") or body.get("total_count") or 0)
                    if page * 100 >= total or not rows:
                        break
                    page += 1
            except Exception as error:
                mapped = classify_alibaba_error(error)
                text = str(mapped)
                if "KmsServiceNotEnabled" in text or "Kms service not Enabled" in text:
                    logger.warning(
                        "Alibaba KMS Secrets Manager is not enabled for account=%s. Enable KMS Secrets Manager in the Alibaba console, then retry.",
                        account.alias,
                    )
                else:
                    logger.warning("Alibaba KMS list failed account=%s detail=%s", account.alias, mapped)
        return items
    finally:
        session.close()


def reveal_alibaba_secret_pairs(secret_id: str) -> list[dict[str, str]]:
    names = [secret_id]
    if secret_id.startswith("aliyun-kms-"):
        remainder = secret_id[len("aliyun-kms-") :]
        names.append(remainder)
    session = SessionLocal()
    try:
        for account in _enabled_alibaba_accounts(session):
            environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
            binding = account_binding(account, environments_for_account(account, environments))
            try:
                client = AlibabaClientFactory(binding.connection_config()).kms_client()
                for name in names:
                    try:
                        raw = _secret_data(client, name)
                        pairs = _pairs_from_secret_string(raw)
                        raw = ""
                        if pairs:
                            logger.info("Alibaba secret reveal requested name=%s account=%s", name, account.alias)
                            return [{"name": key, "revealed": value} for key, value in pairs]
                    except Exception:
                        continue
            except Exception as error:
                logger.warning("Alibaba secret reveal skipped account=%s detail=%s", account.alias, classify_alibaba_error(error))
        raise LookupError("Secret was not found in configured Alibaba accounts")
    finally:
        session.close()
