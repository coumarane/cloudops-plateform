from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import Principal, principal_from_headers, require_permission
from app.providers.alibaba.exceptions import classify_alibaba_error
from app.providers.alibaba.secrets import reveal_alibaba_secret_pairs
from app.providers.aws.errors import classify_aws_error
from app.providers.aws.secrets import reveal_aws_secret_pairs
from app.providers.azure.errors import classify_azure_error
from app.providers.azure.secrets import reveal_azure_secret_pairs
from app.providers.gcp.errors import classify_gcp_error
from app.providers.gcp.secrets import reveal_gcp_secret_pairs

router = APIRouter()


class SecretRevealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    secretId: str = Field(..., min_length=1, max_length=2048)
    environment: str | None = Field(default=None, max_length=32)


def _reveal(secret_id: str) -> list[dict[str, str]]:
    if secret_id.startswith("arn:aws:"):
        return reveal_aws_secret_pairs(secret_id)
    if secret_id.startswith("azure-kv-") or secret_id.startswith("https://"):
        return reveal_azure_secret_pairs(secret_id)
    if secret_id.startswith("gcp-sm-") or secret_id.startswith("projects/"):
        return reveal_gcp_secret_pairs(secret_id)
    # Prefer Alibaba/AWS fallbacks for legacy catalog ids.
    try:
        return reveal_alibaba_secret_pairs(secret_id)
    except LookupError:
        pass
    try:
        return reveal_azure_secret_pairs(secret_id)
    except LookupError:
        pass
    try:
        return reveal_gcp_secret_pairs(secret_id)
    except LookupError:
        pass
    return reveal_aws_secret_pairs(secret_id)


@router.post("/secrets/reveal")
def reveal_secret(body: SecretRevealRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "credential:reveal")
    if (body.environment or "").upper() == "PRD":
        require_permission(principal, "credential:prod_update")
    try:
        items = _reveal(body.secretId)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        secret_id = body.secretId
        if secret_id.startswith("arn:aws:"):
            detail = str(classify_aws_error(error))
        elif secret_id.startswith("azure-kv-") or secret_id.startswith("https://"):
            detail = str(classify_azure_error(error))
        elif secret_id.startswith("gcp-sm-") or secret_id.startswith("projects/"):
            detail = str(classify_gcp_error(error))
        else:
            detail = str(classify_alibaba_error(error))
        raise HTTPException(status_code=400, detail=detail) from error
    return {"items": items}
