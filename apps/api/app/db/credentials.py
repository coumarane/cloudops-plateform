from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CredentialAuditRow,
    CredentialRotationEventRow,
    CredentialRow,
    CredentialValidationRow,
    CredentialVersionRow,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CredentialRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, credential_id: str) -> CredentialRow | None:
        return self.session.get(CredentialRow, credential_id)

    def find_by_scope_name(
        self,
        *,
        provider: str,
        region: str,
        account: str,
        environment: str,
        name: str,
    ) -> CredentialRow | None:
        return self.session.scalar(
            select(CredentialRow).where(
                CredentialRow.provider == provider,
                CredentialRow.platform_region == region,
                CredentialRow.account_alias == account,
                CredentialRow.environment == environment,
                CredentialRow.name == name,
            )
        )

    def list(
        self,
        *,
        provider: str | None = None,
        region: str | None = None,
        environment: str | None = None,
        account: str | None = None,
        status: str | None = None,
    ) -> list[CredentialRow]:
        stmt = select(CredentialRow)
        if provider:
            stmt = stmt.where(CredentialRow.provider == provider)
        if region:
            stmt = stmt.where(CredentialRow.platform_region == region)
        if environment:
            stmt = stmt.where(CredentialRow.environment == environment)
        if account:
            stmt = stmt.where(CredentialRow.account_alias == account)
        if status:
            stmt = stmt.where(CredentialRow.status == status)
        return list(self.session.scalars(stmt.order_by(CredentialRow.name)))

    def add(self, row: CredentialRow) -> CredentialRow:
        self.session.add(row)
        self.session.flush()
        return row

    def add_version(self, credential: CredentialRow, *, actor: str) -> CredentialVersionRow:
        count = len(
            list(self.session.scalars(select(CredentialVersionRow).where(CredentialVersionRow.credential_id == credential.id)))
        )
        row = CredentialVersionRow(
            id=str(uuid4()),
            credential_id=credential.id,
            version=count + 1,
            fingerprint=credential.fingerprint,
            secret_reference=credential.secret_reference,
            created_at=utcnow(),
            created_by=actor,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def add_validation(self, row: CredentialValidationRow) -> CredentialValidationRow:
        self.session.add(row)
        self.session.flush()
        return row

    def add_rotation_event(self, row: CredentialRotationEventRow) -> CredentialRotationEventRow:
        self.session.add(row)
        self.session.flush()
        return row

    def add_audit(self, row: CredentialAuditRow) -> CredentialAuditRow:
        self.session.add(row)
        self.session.flush()
        return row

    def list_versions(self, credential_id: str) -> list[CredentialVersionRow]:
        return list(
            self.session.scalars(
                select(CredentialVersionRow)
                .where(CredentialVersionRow.credential_id == credential_id)
                .order_by(CredentialVersionRow.version.desc())
            )
        )

    def list_validations(self, credential_id: str) -> list[CredentialValidationRow]:
        return list(
            self.session.scalars(
                select(CredentialValidationRow)
                .where(CredentialValidationRow.credential_id == credential_id)
                .order_by(CredentialValidationRow.created_at.desc())
            )
        )

    def list_history(self, credential_id: str) -> list[CredentialRotationEventRow]:
        return list(
            self.session.scalars(
                select(CredentialRotationEventRow)
                .where(CredentialRotationEventRow.credential_id == credential_id)
                .order_by(CredentialRotationEventRow.created_at.desc())
            )
        )

    def list_audit(self) -> list[CredentialAuditRow]:
        return list(self.session.scalars(select(CredentialAuditRow).order_by(CredentialAuditRow.created_at.desc())))
