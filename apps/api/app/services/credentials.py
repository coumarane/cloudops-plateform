from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.correlation import current_correlation_id
from app.core.logging import get_logger, sanitize_text
from app.core.rbac import Principal, require_permission
from app.db.credentials import CredentialRepository, utcnow
from app.db.models import (
    CredentialAuditRow,
    CredentialRotationEventRow,
    CredentialRow,
    CredentialValidationRow,
)
from app.db.session import SessionLocal
from app.domain.enums import CLOUD_REGIONS, PRODUCTION
from app.domain.models import (
    AuditEvent,
    CredentialHistoryEvent,
    CredentialRecord,
    CredentialValidationRecord,
    SecretHistoryEvent,
    SecretRecord,
    Scope,
)
from app.secrets.factory import assert_backend_allowed, secret_backend
from app.secrets.fingerprint import assert_secret_size, fingerprint_secret, parse_secret_payload
from app.secrets.backends.local import LocalSecretBackendError
from app.topology.models import environment_scope_id

logger = get_logger(__name__)

ROLE_TYPES = {"iam_role", "sts_assume_role", "ram_role", "sts"}
STATUS_MAP = {
    "HEALTHY": "OK",
    "ROTATION_DUE": "Due soon",
    "OVERDUE": "Overdue",
    "INVALID": "Overdue",
    "DISABLED": "OK",
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _age(moment: datetime | None) -> str:
    if moment is None:
        return "—"
    now = datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    seconds = int((now - moment).total_seconds())
    if seconds < 0:
        days = abs(seconds) // 86400
        return f"in {days}d" if days else "due"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def compute_status(row: CredentialRow, *, now: datetime | None = None) -> str:
    if row.status in {"INVALID", "DISABLED"}:
        return row.status
    due = row.rotation_due_at
    if due is None:
        return "HEALTHY"
    current = now or utcnow()
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    if current > due:
        return "OVERDUE"
    soon = due - timedelta(days=max(1, settings.rotation_due_soon_days))
    if current >= soon:
        return "ROTATION_DUE"
    return "HEALTHY"


def to_record(row: CredentialRow) -> CredentialRecord:
    return CredentialRecord(
        id=row.id,
        name=row.name,
        provider=row.provider,  # type: ignore[arg-type]
        region=row.platform_region,  # type: ignore[arg-type]
        account=row.account_alias,
        environment=row.environment,  # type: ignore[arg-type]
        accountId=row.account_id,
        environmentId=row.environment_id,
        credentialType=row.credential_type,
        secretBackend=row.secret_backend,
        secretReference=row.secret_reference,
        fingerprint=row.fingerprint,
        status=row.status,
        lastValidatedAt=_iso(row.last_validated_at),
        lastRotatedAt=_iso(row.last_rotated_at),
        rotationDueAt=_iso(row.rotation_due_at),
        rotationPolicyDays=row.rotation_policy_days,
        createdAt=row.created_at.isoformat(),
        updatedAt=row.updated_at.isoformat(),
        updatedBy=row.updated_by,
        roleArn=row.role_arn,
        externalIdRef=row.external_id_ref,
        cloudRegion=row.cloud_region,
    )


def to_secret_record(row: CredentialRow, history: list[SecretHistoryEvent] | None = None) -> SecretRecord:
    due = row.rotation_due_at
    if due is None:
        next_due = "—"
    else:
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        delta = due - utcnow()
        next_due = "Overdue" if delta.total_seconds() < 0 else f"{max(delta.days, 0)}d"
    return SecretRecord(
        id=row.id,
        name=row.name,
        namespace=row.credential_type,
        provider=row.provider,  # type: ignore[arg-type]
        region=row.platform_region,  # type: ignore[arg-type]
        environment=row.environment,  # type: ignore[arg-type]
        account=row.account_alias,
        status=STATUS_MAP.get(row.status, "OK"),  # type: ignore[arg-type]
        lastRotated=_age(row.last_rotated_at),
        nextDue=next_due,
        lastValidated=_age(row.last_validated_at),
        history=history or [],
        credentialType=row.credential_type,
        secretBackend=row.secret_backend,
        fingerprint=row.fingerprint or None,
        updatedBy=row.updated_by or None,
        lifecycleStatus=row.status,
        source="live",
    )


def _assert_production(principal: Principal, environment: str, *, confirmed: bool, reason: str) -> None:
    if environment not in PRODUCTION:
        return
    require_permission(principal, "credential:prod_update")
    if not confirmed:
        raise HTTPException(status_code=400, detail="Production credential changes require explicit confirmation")
    if not reason.strip():
        raise HTTPException(status_code=400, detail="Production credential changes require a reason")


def _reference_for(row: CredentialRow) -> str:
    if row.secret_reference:
        return row.secret_reference
    slug = f"cloudops/{row.provider.lower()}/{row.platform_region.lower()}/{row.environment.lower()}/{row.name}"
    return slug.replace(" ", "-")


def _audit(repo: CredentialRepository, row: CredentialRow, *, action: str, actor: str, result: str, reason: str, ticket: str) -> None:
    repo.add_audit(
        CredentialAuditRow(
            id=str(uuid4()),
            action=action,
            credential_id=row.id,
            credential_name=row.name,
            actor=actor,
            provider=row.provider,
            platform_region=row.platform_region,
            account_alias=row.account_alias,
            environment=row.environment,
            result=result,
            reason=sanitize_text(reason),
            change_ticket=ticket,
            correlation_id=current_correlation_id(),
            created_at=utcnow(),
        )
    )


def _cloud_region(provider: str, region: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    return CLOUD_REGIONS.get(f"{provider}-{region}", "")


def create_credential(payload: dict, principal: Principal) -> CredentialRecord:
    require_permission(principal, "credential:create")
    environment = payload["environment"]
    _assert_production(
        principal,
        environment,
        confirmed=bool(payload.get("confirmed")),
        reason=str(payload.get("reason") or ""),
    )
    backend_name = str(payload.get("secretBackend") or settings.secret_backend)
    try:
        assert_backend_allowed(backend_name)
    except LocalSecretBackendError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    credential_type = str(payload["credentialType"])
    secret = payload.get("secretValue")
    try:
        if secret:
            assert_secret_size(secret, settings.max_secret_bytes)
            parse_secret_payload(secret, credential_type, payload["provider"])
        elif credential_type.lower() not in ROLE_TYPES:
            raise HTTPException(status_code=400, detail="Secret value is required for this credential type")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=sanitize_text(str(error))) from error
    session = SessionLocal()
    try:
        repo = CredentialRepository(session)
        duplicate = repo.find_by_scope_name(
            provider=payload["provider"],
            region=payload["region"],
            account=payload["account"],
            environment=environment,
            name=payload["name"],
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="A credential with this name already exists in the environment")
        now = utcnow()
        policy = int(payload.get("rotationPolicyDays") or 90)
        row = CredentialRow(
            id=f"cred-{uuid4().hex[:12]}",
            name=payload["name"],
            provider=payload["provider"],
            platform_region=payload["region"],
            account_alias=payload["account"],
            account_id=str(payload.get("accountId") or ""),
            environment=environment,
            environment_id=environment_scope_id(payload["account"], environment),
            credential_type=credential_type,
            secret_backend=backend_name,
            secret_reference="",
            fingerprint="",
            status="HEALTHY",
            rotation_policy_days=policy,
            last_rotated_at=now if secret else None,
            rotation_due_at=(now + timedelta(days=policy)) if secret else now + timedelta(days=policy),
            created_at=now,
            updated_at=now,
            updated_by=principal.user,
            role_arn=str(payload.get("roleArn") or ""),
            external_id_ref=str(payload.get("externalIdRef") or ""),
            cloud_region=_cloud_region(payload["provider"], payload["region"], payload.get("cloudRegion")),
        )
        if credential_type.lower() in ROLE_TYPES and not row.role_arn:
            raise HTTPException(status_code=400, detail="Role ARN is required for role-based credentials")
        row.secret_reference = _reference_for(row)
        if secret:
            backend = secret_backend(backend_name, region=row.cloud_region or None)
            meta = backend.store_secret(row.secret_reference, secret)
            row.secret_reference = meta.reference
            row.fingerprint = fingerprint_secret(secret)
        repo.add(row)
        if secret:
            repo.add_version(row, actor=principal.user)
            repo.add_rotation_event(
                CredentialRotationEventRow(
                    id=str(uuid4()),
                    credential_id=row.id,
                    action="Replace",
                    result="Succeeded",
                    detail="Secret stored in backend. Value was not persisted in PostgreSQL.",
                    actor=principal.user,
                    created_at=now,
                )
            )
        _audit(
            repo,
            row,
            action="CREDENTIAL_CREATED",
            actor=principal.user,
            result="Succeeded",
            reason=str(payload.get("reason") or ""),
            ticket=str(payload.get("changeTicket") or ""),
        )
        session.commit()
        return to_record(row)
    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="A credential with this name already exists in the environment") from error
    finally:
        session.close()
        secret = None


def replace_credential(credential_id: str, payload: dict, principal: Principal) -> CredentialRecord:
    require_permission(principal, "credential:rotate")
    secret = str(payload.get("secretValue") or "")
    session = SessionLocal()
    try:
        try:
            assert_secret_size(secret, settings.max_secret_bytes)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=sanitize_text(str(error))) from error
        repo = CredentialRepository(session)
        row = repo.get(credential_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        _assert_production(
            principal,
            row.environment,
            confirmed=bool(payload.get("confirmed")),
            reason=str(payload.get("reason") or ""),
        )
        try:
            parse_secret_payload(secret, row.credential_type, row.provider)
            assert_backend_allowed(row.secret_backend)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=sanitize_text(str(error))) from error
        except LocalSecretBackendError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        backend = secret_backend(row.secret_backend, region=row.cloud_region or None)
        if not row.secret_reference:
            row.secret_reference = _reference_for(row)
        if backend.validate_reference(row.secret_reference):
            meta = backend.replace_secret(row.secret_reference, secret)
        else:
            meta = backend.store_secret(row.secret_reference, secret)
        now = utcnow()
        row.secret_reference = meta.reference
        row.fingerprint = fingerprint_secret(secret)
        row.last_rotated_at = now
        row.rotation_due_at = now + timedelta(days=row.rotation_policy_days)
        row.status = "HEALTHY"
        row.updated_at = now
        row.updated_by = principal.user
        repo.add_version(row, actor=principal.user)
        repo.add_rotation_event(
            CredentialRotationEventRow(
                id=str(uuid4()),
                credential_id=row.id,
                action="Replace",
                result="Succeeded",
                detail="Secret replaced in backend. Value was not persisted in PostgreSQL.",
                actor=principal.user,
                created_at=now,
            )
        )
        _audit(
            repo,
            row,
            action="CREDENTIAL_REPLACED",
            actor=principal.user,
            result="Succeeded",
            reason=str(payload.get("reason") or ""),
            ticket=str(payload.get("changeTicket") or ""),
        )
        session.commit()
        logger.info("Credential replaced id=%s backend=%s", row.id, row.secret_backend)
        return to_record(row)
    except HTTPException:
        session.rollback()
        raise
    finally:
        session.close()
        secret = None


def update_credential(credential_id: str, payload: dict, principal: Principal) -> CredentialRecord:
    require_permission(principal, "credential:update")
    session = SessionLocal()
    try:
        repo = CredentialRepository(session)
        row = repo.get(credential_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        _assert_production(
            principal,
            row.environment,
            confirmed=bool(payload.get("confirmed")),
            reason=str(payload.get("reason") or ""),
        )
        if "rotationPolicyDays" in payload and payload["rotationPolicyDays"] is not None:
            row.rotation_policy_days = int(payload["rotationPolicyDays"])
            base = row.last_rotated_at or row.created_at
            row.rotation_due_at = base + timedelta(days=row.rotation_policy_days)
        if payload.get("roleArn"):
            row.role_arn = str(payload["roleArn"])
        if payload.get("externalIdRef") is not None:
            row.external_id_ref = str(payload.get("externalIdRef") or "")
        if payload.get("status") == "DISABLED":
            row.status = "DISABLED"
        row.updated_at = utcnow()
        row.updated_by = principal.user
        if row.status not in {"INVALID", "DISABLED"}:
            row.status = compute_status(row)
        repo.add_rotation_event(
            CredentialRotationEventRow(
                id=str(uuid4()),
                credential_id=row.id,
                action="Update",
                result="Succeeded",
                detail="Metadata updated. Secret value was not retrieved.",
                actor=principal.user,
                created_at=utcnow(),
            )
        )
        _audit(
            repo,
            row,
            action="ROTATION_DUE_CHANGED",
            actor=principal.user,
            result="Succeeded",
            reason=str(payload.get("reason") or ""),
            ticket=str(payload.get("changeTicket") or ""),
        )
        session.commit()
        return to_record(row)
    except HTTPException:
        session.rollback()
        raise
    finally:
        session.close()


def list_credentials(scope: Scope, status: str | None = None) -> list[CredentialRecord]:
    session = SessionLocal()
    try:
        mapped_status = None
        if status:
            raw = status.upper().replace("-", "_").replace(" ", "_")
            aliases = {
                "ROTATIONDUE": "ROTATION_DUE",
                "DUE_SOON": "ROTATION_DUE",
                "OK": "HEALTHY",
                "HEALTHY": "HEALTHY",
                "OVERDUE": "OVERDUE",
                "INVALID": "INVALID",
                "DISABLED": "DISABLED",
                "ROTATION_DUE": "ROTATION_DUE",
            }
            mapped_status = aliases.get(raw, raw)
        rows = CredentialRepository(session).list(
            provider=scope.provider,
            region=scope.region,
            environment=scope.environment,
            account=scope.account,
            status=mapped_status,
        )
        return [to_record(row) for row in rows]
    finally:
        session.close()


def get_credential(credential_id: str) -> CredentialRecord:
    session = SessionLocal()
    try:
        row = CredentialRepository(session).get(credential_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        return to_record(row)
    finally:
        session.close()


def list_history(credential_id: str) -> list[CredentialHistoryEvent]:
    session = SessionLocal()
    try:
        repo = CredentialRepository(session)
        if repo.get(credential_id) is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        return [
            CredentialHistoryEvent(
                id=row.id,
                action=row.action,
                result=row.result,
                detail=row.detail,
                actor=row.actor,
                createdAt=row.created_at.isoformat(),
            )
            for row in repo.list_history(credential_id)
        ]
    finally:
        session.close()


def list_validations(credential_id: str) -> list[CredentialValidationRecord]:
    session = SessionLocal()
    try:
        repo = CredentialRepository(session)
        if repo.get(credential_id) is None:
            raise HTTPException(status_code=404, detail="Credential not found")
        return [
            CredentialValidationRecord(
                id=row.id,
                credentialId=row.credential_id,
                success=row.success,
                status=row.status,
                latencyMs=row.latency_ms,
                errorCategory=row.error_category,
                providerAccount=row.provider_account,
                correlationId=row.correlation_id,
                createdAt=row.created_at.isoformat(),
            )
            for row in repo.list_validations(credential_id)
        ]
    finally:
        session.close()


def overlay_secret_records(items: list[SecretRecord]) -> list[SecretRecord]:
    session = SessionLocal()
    try:
        repo = CredentialRepository(session)
        live_rows = repo.list()
        if not live_rows:
            return items
        live: list[SecretRecord] = []
        keys: set[tuple[str, str, str, str]] = set()
        for row in live_rows:
            history = [
                SecretHistoryEvent(
                    at=_age(event.created_at),
                    actor=event.actor,
                    action=event.action if event.action in {"Update", "Rotate", "Validate", "Replace"} else "Update",  # type: ignore[arg-type]
                    result="Succeeded" if event.result == "Succeeded" else "Failed",  # type: ignore[arg-type]
                    detail=event.detail,
                )
                for event in repo.list_history(row.id)[:5]
            ]
            live.append(to_secret_record(row, history))
            keys.add((row.provider, row.platform_region, row.environment, row.name))
        kept = [item for item in items if (item.provider, item.region, item.environment, item.name) not in keys]
        return live + kept
    except Exception:
        logger.exception("Live credential overlay unavailable; using mock secrets")
        return items
    finally:
        session.close()


def overlay_audit_events(items: list[AuditEvent]) -> list[AuditEvent]:
    session = SessionLocal()
    try:
        live = [
            AuditEvent(
                id=row.id,
                event=row.action.replace("_", " ").title(),
                actor=row.actor,
                objectName=row.credential_name or row.credential_id,
                detail=sanitize_text(f"{row.result}. {row.reason}".strip()),
                age=_age(row.created_at),
                provider=row.provider or "AWS",  # type: ignore[arg-type]
                region=row.platform_region or "EMEA",  # type: ignore[arg-type]
                environment=row.environment or "DEV",  # type: ignore[arg-type]
            )
            for row in CredentialRepository(session).list_audit()
        ]
        return live + items
    except Exception:
        logger.exception("Live credential audit overlay unavailable")
        return items
    finally:
        session.close()


def scan_rotation_statuses() -> int:
    session = SessionLocal()
    try:
        repo = CredentialRepository(session)
        changed = 0
        for row in repo.list():
            next_status = compute_status(row)
            if next_status != row.status and row.status not in {"INVALID", "DISABLED"}:
                row.status = next_status
                row.updated_at = utcnow()
                changed += 1
        session.commit()
        logger.info("Rotation status scan updated %s credentials", changed)
        return changed
    finally:
        session.close()


def record_validation_result(
    credential_id: str,
    *,
    success: bool,
    latency_ms: int,
    error_category: str = "",
    provider_account: str = "",
) -> None:
    session = SessionLocal()
    try:
        repo = CredentialRepository(session)
        row = repo.get(credential_id)
        if row is None:
            return
        now = utcnow()
        row.last_validated_at = now
        row.updated_at = now
        if success:
            if row.status == "INVALID":
                row.status = compute_status(row)
        else:
            row.status = "INVALID"
        repo.add_validation(
            CredentialValidationRow(
                id=str(uuid4()),
                credential_id=credential_id,
                success=success,
                status="ok" if success else "failed",
                latency_ms=latency_ms,
                error_category=error_category,
                provider_account=provider_account,
                correlation_id=current_correlation_id(),
                created_at=now,
            )
        )
        repo.add_rotation_event(
            CredentialRotationEventRow(
                id=str(uuid4()),
                credential_id=credential_id,
                action="Validate",
                result="Succeeded" if success else "Failed",
                detail="Identity call succeeded" if success else sanitize_text(error_category or "Validation failed"),
                actor="credential-validate",
                created_at=now,
            )
        )
        _audit(
            repo,
            row,
            action="CREDENTIAL_VALIDATED" if success else "CREDENTIAL_VALIDATION_FAILED",
            actor="credential-validate",
            result="Succeeded" if success else "Failed",
            reason="",
            ticket="",
        )
        session.commit()
    finally:
        session.close()
