from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.db.models import CloudAccountRow, CloudEnvironmentRow, ManagedProviderRow, PlatformJobRow
from app.db.session import SessionLocal
from app.platform.bindings import account_binding, environments_for_account
from app.topology.alibaba import load_alibaba_topology
from app.topology.loader import load_topology
from app.topology.models import AccountBinding


def accounts_for_job(job_id: str, provider: str) -> list[AccountBinding]:
    session = SessionLocal()
    try:
        job = session.get(PlatformJobRow, job_id)
        target = job.target_id if job else ""
        managed = session.query(ManagedProviderRow).count() > 0
        rows = list(
            session.scalars(
                select(CloudAccountRow).where(CloudAccountRow.provider == provider, CloudAccountRow.enabled.is_(True))
            )
        )
        env_rows = list(session.scalars(select(CloudEnvironmentRow)))
        selected: list[CloudAccountRow] = rows
        env_filter: tuple[str, ...] | None = None
        if target:
            env = session.get(CloudEnvironmentRow, target)
            account = session.get(CloudAccountRow, target)
            if env is not None:
                account = session.get(CloudAccountRow, env.account_id)
                selected = [account] if account is not None else []
                env_filter = (env.environment,)
            elif account is not None:
                selected = [account]
        bindings: list[AccountBinding] = []
        for row in selected:
            if row is None:
                continue
            environments = env_filter or environments_for_account(row, env_rows)
            if not environments:
                continue
            bindings.append(account_binding(row, environments))
        if bindings:
            return bindings
        if managed and target:
            return []
        if settings.demo_mode or settings.seed_topology or not managed:
            topology = load_alibaba_topology() if provider == "Alibaba" else load_topology()
            return list(topology.accounts)
        return []
    finally:
        session.close()
