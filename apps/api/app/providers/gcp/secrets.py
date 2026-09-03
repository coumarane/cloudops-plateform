from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import CloudAccountRow, CloudEnvironmentRow, ManagedProviderRow
from app.db.session import SessionLocal
from app.domain.enums import Environment
from app.domain.models import SecretRecord
from app.platform.bindings import environments_for_account
from app.providers.gcp.auth import resolve_project_id
from app.providers.gcp.client import GcpClientFactory
from app.providers.gcp.errors import classify_gcp_error
from app.providers.gcp.models import GcpConnectionConfig

logger = get_logger(__name__)


def _iso(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if hasattr(value, "seconds"):
        return datetime.fromtimestamp(int(value.seconds), tz=timezone.utc).isoformat()
    return str(value)


def _environment_for_account(account: CloudAccountRow, environments: tuple[str, ...]) -> Environment:
    for code in ("DEV", "INT/TST", "UAT", "NPD", "PRD"):
        if code in environments:
            return code  # type: ignore[return-value]
    return "DEV"


def _pairs_from_secret_string(raw: str) -> list[tuple[str, str]]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [("value", raw)]
    if isinstance(parsed, dict):
        return [(str(key), "" if value is None else str(value)) for key, value in parsed.items()]
    return [("value", raw)]


def _gcp_accounts(session):
    return list(
        session.scalars(
            select(CloudAccountRow)
            .join(ManagedProviderRow, CloudAccountRow.managed_provider_id == ManagedProviderRow.id)
            .where(
                CloudAccountRow.provider == "GCP",
                CloudAccountRow.enabled.is_(True),
                ManagedProviderRow.enabled.is_(True),
            )
            .order_by(CloudAccountRow.alias)
        )
    )


def _config_for(account: CloudAccountRow | None, environments: tuple[str, ...] = ("DEV",)) -> GcpConnectionConfig:
    project = (account.account_id if account else None) or resolve_project_id()
    return GcpConnectionConfig(
        cloud_region=(account.cloud_region if account else None) or "europe-west1",
        account_id=project or None,
        project_id=project or None,
        credentials_file=None,
        platform_region=(account.platform_region if account else None) or "EMEA",
        environment=environments[0] if environments else "DEV",
        account_alias=(account.alias if account else "gcp"),
        credential_ref=(account.credential_ref if account else None),
    )


def list_live_gcp_secrets() -> list[SecretRecord]:
    session = SessionLocal()
    try:
        items: list[SecretRecord] = []
        seen: set[str] = set()
        accounts = _gcp_accounts(session)
        configs: list[tuple[str, str, Environment, GcpConnectionConfig]] = []
        if accounts:
            for account in accounts:
                environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
                env_codes = environments_for_account(account, environments)
                configs.append(
                    (
                        account.display_name or account.alias,
                        account.platform_region if account.platform_region in {"AMER", "EMEA", "APAC"} else "EMEA",
                        _environment_for_account(account, env_codes),
                        _config_for(account, env_codes),
                    )
                )
        elif resolve_project_id():
            configs.append(("GCP", "EMEA", "DEV", _config_for(None)))
        for account_name, region, environment, config in configs:
            try:
                factory = GcpClientFactory(config)
                client = factory.secret_manager()
                parent = f"projects/{factory.project_id()}"
                for secret in client.list_secrets(request={"parent": parent}):
                    full_name = str(secret.name or "")
                    short = full_name.rsplit("/", 1)[-1]
                    if not short or short in seen:
                        continue
                    seen.add(short)
                    keys: list[str] = []
                    try:
                        version = client.access_secret_version(request={"name": f"{full_name}/versions/latest"})
                        raw = version.payload.data.decode("utf-8")
                        keys = [key for key, _ in _pairs_from_secret_string(raw)]
                        raw = ""
                    except Exception as error:
                        logger.warning("GCP secret keys unavailable name=%s detail=%s", short, classify_gcp_error(error))
                    items.append(
                        SecretRecord(
                            id=f"gcp-sm-{factory.project_id()}-{short}",
                            name=short,
                            namespace="GCP/SecretManager",
                            provider="GCP",
                            region=region,  # type: ignore[arg-type]
                            environment=environment,
                            account=account_name,
                            status="OK",
                            lastRotated=_iso(getattr(secret, "create_time", None)),
                            nextDue="—",
                            lastValidated="—",
                            credentialType="application",
                            secretBackend="gcp",
                            lifecycleStatus="HEALTHY",
                            source="live",
                            keys=[key for key in keys if key != "value" or len(keys) == 1],
                            arn=full_name or short,
                            description=None,
                            cloudRegion=config.cloud_region,
                        )
                    )
            except Exception as error:
                logger.warning("GCP Secret Manager list failed account=%s detail=%s", account_name, classify_gcp_error(error))
        return items
    finally:
        session.close()


def reveal_gcp_secret_pairs(secret_id: str) -> list[dict[str, str]]:
    names = [secret_id]
    if secret_id.startswith("projects/"):
        names.append(secret_id.rsplit("/", 1)[-1])
    if secret_id.startswith("gcp-sm-"):
        names.append(secret_id.rsplit("-", 1)[-1])
        remainder = secret_id[len("gcp-sm-") :]
        names.append(remainder.split("-", 1)[-1] if "-" in remainder else remainder)
    session = SessionLocal()
    try:
        accounts = _gcp_accounts(session)
        configs = []
        if accounts:
            for account in accounts:
                environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
                configs.append(_config_for(account, environments_for_account(account, environments)))
        else:
            configs.append(_config_for(None))
        for config in configs:
            try:
                factory = GcpClientFactory(config)
                client = factory.secret_manager()
                project = factory.project_id()
                for name in names:
                    resource = name if name.startswith("projects/") else f"projects/{project}/secrets/{name}"
                    try:
                        version = client.access_secret_version(request={"name": f"{resource}/versions/latest"})
                        raw = version.payload.data.decode("utf-8")
                        pairs = _pairs_from_secret_string(raw)
                        raw = ""
                        if pairs:
                            logger.info("GCP secret reveal requested name=%s", name)
                            return [{"name": key, "revealed": value} for key, value in pairs]
                    except Exception:
                        continue
            except Exception as error:
                logger.warning("GCP secret reveal skipped detail=%s", classify_gcp_error(error))
        raise LookupError("Secret was not found in configured GCP projects")
    finally:
        session.close()
