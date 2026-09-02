from __future__ import annotations

import json
import os
import time

from app.core.logging import get_logger, sanitize_text
from app.db.credentials import CredentialRepository
from app.db.models import PlatformJobRow
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.domain.enums import PRODUCTION
from app.secrets.factory import secret_backend
from app.services.credentials import ROLE_TYPES, record_validation_result, scan_rotation_statuses

logger = get_logger(__name__)

_TEMP_KEY_ID = "CLOUDOPS_CRED_VALIDATE_ACCESS_KEY_ID"
_TEMP_KEY_SECRET = "CLOUDOPS_CRED_VALIDATE_ACCESS_KEY_SECRET"


def _classify(error: Exception) -> str:
    text = sanitize_text(str(error)).lower()
    if "denied" in text or "forbidden" in text:
        return "permission"
    if "credential" in text or "access key" in text or "auth" in text:
        return "authentication"
    if "timeout" in text or "throttl" in text or "unavailable" in text:
        return "transient"
    return "provider"


def _clear_temp_env() -> None:
    os.environ.pop(_TEMP_KEY_ID, None)
    os.environ.pop(_TEMP_KEY_SECRET, None)


def _validate_aws(row, material: str | None) -> str:
    import boto3
    from botocore.config import Config

    kwargs: dict = {"region_name": row.cloud_region or "eu-west-1"}
    if material and row.credential_type.lower() in {"access_key", "application"}:
        try:
            payload = json.loads(material)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict):
            kwargs["aws_access_key_id"] = payload.get("AccessKeyId") or payload.get("aws_access_key_id")
            kwargs["aws_secret_access_key"] = payload.get("SecretAccessKey") or payload.get("aws_secret_access_key")
            if payload.get("SessionToken") or payload.get("session_token"):
                kwargs["aws_session_token"] = payload.get("SessionToken") or payload.get("session_token")
    session = boto3.Session(**{k: v for k, v in kwargs.items() if v})
    if row.role_arn and row.credential_type.lower() in ROLE_TYPES:
        sts = session.client("sts", config=Config(retries={"max_attempts": 3, "mode": "standard"}))
        assume = {"RoleArn": row.role_arn, "RoleSessionName": "cloudops-cred-validate"}
        if row.external_id_ref:
            assume["ExternalId"] = row.external_id_ref
        creds = sts.assume_role(**assume)["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=row.cloud_region or "eu-west-1",
        )
        creds = None
    identity = session.client("sts").get_caller_identity()
    return str(identity.get("Account") or "")


def _validate_alibaba(row, material: str | None) -> str:
    from app.providers.alibaba.auth import get_caller_identity
    from app.providers.alibaba.models import AlibabaConnectionConfig

    key_id_ref = None
    secret_ref = None
    try:
        if material and row.credential_type.lower() not in ROLE_TYPES:
            try:
                payload = json.loads(material)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                os.environ[_TEMP_KEY_ID] = str(payload.get("AccessKeyId") or "")
                os.environ[_TEMP_KEY_SECRET] = str(
                    payload.get("AccessKeySecret") or payload.get("access_key_secret") or ""
                )
                key_id_ref = _TEMP_KEY_ID
                secret_ref = _TEMP_KEY_SECRET
        else:
            suffix = "PROD" if row.environment in PRODUCTION else "NONPROD"
            key_id_ref = f"CLOUDOPS_ALIBABA_{suffix}_ACCESS_KEY_ID"
            secret_ref = f"CLOUDOPS_ALIBABA_{suffix}_ACCESS_KEY_SECRET"
        config = AlibabaConnectionConfig(
            cloud_region=row.cloud_region or "cn-hangzhou",
            account_id=row.account_id or None,
            role_arn=row.role_arn or None,
            session_name="cloudops-cred-validate",
            access_key_id_ref=key_id_ref,
            access_key_secret_ref=secret_ref,
            credential_ref=f"env:{secret_ref}" if secret_ref else None,
            platform_region=row.platform_region,
            environment=row.environment,
            account_alias=row.account_alias,
            cluster_environment_tag="Environment",
        )
        identity = get_caller_identity(config)
        return identity.account_id
    finally:
        _clear_temp_env()


def run_credential_validation(job_id: str, credential_id: str | None = None) -> int:
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_running(job_id)
        session.commit()
        if not credential_id:
            job = session.get(PlatformJobRow, job_id)
            credential_id = job.target_id if job else ""
        row = CredentialRepository(session).get(credential_id) if credential_id else None
    finally:
        session.close()
    if row is None:
        finish = SessionLocal()
        try:
            InventoryRepository(finish).mark_job_finished(job_id, status="failed", detail="Credential not found")
            finish.commit()
        finally:
            finish.close()
        return 0
    material = None
    started = time.monotonic()
    try:
        if row.secret_reference:
            backend = secret_backend(row.secret_backend, region=row.cloud_region or None)
            if backend.validate_reference(row.secret_reference):
                material = backend.get_secret(row.secret_reference)
        if row.provider == "Alibaba":
            account = _validate_alibaba(row, material)
        else:
            account = _validate_aws(row, material)
        latency = int((time.monotonic() - started) * 1000)
        record_validation_result(credential_id, success=True, latency_ms=latency, provider_account=account)
        session = SessionLocal()
        try:
            InventoryRepository(session).mark_job_finished(
                job_id, status="succeeded", detail=sanitize_text(f"Validated {row.name}. Account {account}.")
            )
            session.commit()
        finally:
            session.close()
        return 1
    except Exception as error:
        latency = int((time.monotonic() - started) * 1000)
        category = _classify(error)
        record_validation_result(credential_id, success=False, latency_ms=latency, error_category=category)
        session = SessionLocal()
        try:
            InventoryRepository(session).mark_job_finished(
                job_id,
                status="failed",
                detail=sanitize_text("Credential validation failed"),
                error_class=category,
            )
            session.commit()
        finally:
            session.close()
        return 0
    finally:
        material = None
        _clear_temp_env()


def run_rotation_status_scan(job_id: str) -> int:
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_running(job_id)
        session.commit()
    finally:
        session.close()
    updated = scan_rotation_statuses()
    session = SessionLocal()
    try:
        InventoryRepository(session).mark_job_finished(
            job_id, status="succeeded", detail=f"Updated rotation status for {updated} credentials"
        )
        session.commit()
    finally:
        session.close()
    return updated
