from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import Principal, principal_from_headers, require_permission
from app.providers.alibaba.exceptions import classify_alibaba_error
from app.providers.alibaba.secrets import reveal_alibaba_secret_pairs
from app.providers.aws.errors import classify_aws_error
from app.providers.aws.secrets import reveal_aws_secret_pairs

router = APIRouter()


class SecretRevealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    secretId: str = Field(..., min_length=1, max_length=2048)
    environment: str | None = Field(default=None, max_length=32)


@router.post("/secrets/reveal")
def reveal_secret(body: SecretRevealRequest, principal: Principal = Depends(principal_from_headers)) -> dict:
    require_permission(principal, "credential:reveal")
    if (body.environment or "").upper() == "PRD":
        require_permission(principal, "credential:prod_update")
    try:
        if body.secretId.startswith("arn:aws:"):
            items = reveal_aws_secret_pairs(body.secretId)
        else:
            try:
                items = reveal_alibaba_secret_pairs(body.secretId)
            except LookupError:
                items = reveal_aws_secret_pairs(body.secretId)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        detail = str(classify_alibaba_error(error) if not body.secretId.startswith("arn:aws:") else classify_aws_error(error))
        raise HTTPException(status_code=400, detail=detail) from error
    return {"items": items}
