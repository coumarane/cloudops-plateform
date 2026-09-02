from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.listing import listed
from app.api.v1.params import parse_environment, parse_provider, parse_region, parse_scope
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.core.rbac import Principal, principal_from_headers, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.domain.models import Scope
from app.services.credentials import (
    create_credential,
    get_credential,
    list_credentials,
    list_history,
    list_validations,
    replace_credential,
    update_credential,
)
from app.services.job_kinds import KIND_CREDENTIAL_VALIDATE
from app.services.jobs import enqueue_job
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()


class CredentialWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    provider: str | None = Field(default=None, max_length=32)
    region: str | None = Field(default=None, max_length=32)
    account: str | None = Field(default=None, max_length=128)
    environment: str | None = Field(default=None, max_length=32)
    accountId: str | None = Field(default=None, max_length=32)
    credentialType: str | None = Field(default=None, max_length=64)
    secretBackend: str | None = Field(default=None, max_length=32)
    secretValue: str | None = Field(default=None, max_length=65536)
    roleArn: str | None = Field(default=None, max_length=512)
    externalIdRef: str | None = Field(default=None, max_length=256)
    cloudRegion: str | None = Field(default=None, max_length=64)
    rotationPolicyDays: int | None = Field(default=None, ge=1, le=3650)
    confirmed: bool = False
    reason: str = Field(default="", max_length=500)
    changeTicket: str = Field(default="", max_length=128)
    status: str | None = Field(default=None, max_length=32)


def _dump(payload) -> dict:
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload
    assert_no_secret_values(walk_strings(data))
    if "secretValue" in data:
        raise ValueError("Secret values must never be returned by the CloudOps API.")
    return data


def _normalize(payload: dict) -> dict:
    if payload.get("provider"):
        payload["provider"] = parse_provider(payload["provider"])
    if payload.get("region"):
        payload["region"] = parse_region(payload["region"])
    if payload.get("environment"):
        payload["environment"] = parse_environment(payload["environment"])
    return payload


@router.get("/credentials")
def list_credential_records(
    scope: Scope = Depends(parse_scope),
    status: str | None = Query(default=None),
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "credential:read")
    return listed(list_credentials(scope, status))


@router.get("/credentials/{credential_id}")
def get_credential_record(credential_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "credential:read")
    if credential_id == "secret":
        raise HTTPException(status_code=404, detail="Credential not found")
    return _dump(get_credential(credential_id))


@router.post("/credentials")
def create_credential_record(
    body: CredentialWriteRequest,
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    enforce_rate_limit(f"create:{principal.user}", limit=settings.credential_mutate_rate_per_minute)
    payload = _normalize(body.model_dump())
    for field in ("name", "provider", "region", "account", "environment", "credentialType"):
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")
    secret = payload.pop("secretValue", None)
    try:
        record = create_credential({**payload, "secretValue": secret}, principal)
    finally:
        secret = None
        payload["secretValue"] = None
    return _dump(record)


@router.post("/credentials/{credential_id}/replace")
def replace_credential_record(
    credential_id: str,
    body: CredentialWriteRequest,
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    enforce_rate_limit(f"replace:{principal.user}:{credential_id}", limit=settings.credential_mutate_rate_per_minute)
    if not body.secretValue:
        raise HTTPException(status_code=400, detail="secretValue is required")
    payload = body.model_dump()
    secret = payload.pop("secretValue")
    try:
        record = replace_credential(credential_id, {**payload, "secretValue": secret}, principal)
    finally:
        secret = None
        payload["secretValue"] = None
    return _dump(record)


@router.post("/credentials/{credential_id}")
def update_credential_record(
    credential_id: str,
    body: CredentialWriteRequest,
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    if body.secretValue:
        raise HTTPException(status_code=400, detail="Use /replace to change secret material")
    return _dump(update_credential(credential_id, body.model_dump(), principal))


@router.post("/credentials/{credential_id}/validate")
def validate_credential_record(
    credential_id: str,
    principal: Principal = Depends(principal_from_headers),
) -> dict:
    require_permission(principal, "credential:validate")
    enforce_rate_limit(f"validate:{principal.user}:{credential_id}", limit=settings.credential_validate_rate_per_minute)
    record = get_credential(credential_id)
    job = enqueue_job(
        KIND_CREDENTIAL_VALIDATE,
        target_id=credential_id,
        provider=record.provider,
        platform_region=record.region,
        environment=record.environment,
    )
    payload = {
        "queued": True,
        "jobId": job.id,
        "credentialId": credential_id,
        "status": job.status,
        "detail": job.detail,
    }
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.get("/credentials/{credential_id}/history")
def credential_history(credential_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "credential:read_history")
    return listed(list_history(credential_id))


@router.get("/credentials/{credential_id}/validations")
def credential_validations(credential_id: str, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "credential:read_history")
    return listed(list_validations(credential_id))
