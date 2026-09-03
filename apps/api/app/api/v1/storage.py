from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.config import settings
from app.core.rbac import Principal, principal_from_headers, require_permission
from app.core.security import assert_no_secret_values, walk_strings
from app.db.models import CloudAccountRow, CloudEnvironmentRow, ManagedProviderRow
from app.db.session import SessionLocal
from app.platform.bindings import account_binding, environments_for_account
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.errors import classify_aws_error

router = APIRouter()


@router.get("/storage/buckets")
def list_s3_buckets(principal: Principal = Depends(principal_from_headers)) -> dict:
    """List bucket metadata through configured AWS roles; never return objects or credentials."""
    require_permission(principal, "provider:read")
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
        items: list[dict] = []
        errors: list[dict] = []
        for account in accounts:
            environments = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
            try:
                binding = account_binding(account, environments_for_account(account, environments))
                response = AwsClientFactory(config=binding.connection_config()).client("s3", region_name="us-east-1").list_buckets()
                for bucket in response.get("Buckets", []):
                    created_at = bucket.get("CreationDate")
                    items.append(
                        {
                            "name": str(bucket.get("Name") or ""),
                            "createdAt": created_at.isoformat() if created_at else None,
                            "account": account.display_name or account.alias,
                            "accountId": account.account_id,
                        }
                    )
            except Exception as error:
                errors.append(
                    {
                        "account": account.display_name or account.alias,
                        "accountId": account.account_id,
                        "detail": str(classify_aws_error(error)),
                    }
                )
        payload = {"items": items, "errors": errors, "lastSynced": settings.last_synced}
        assert_no_secret_values(walk_strings(payload))
        return payload
    finally:
        session.close()
