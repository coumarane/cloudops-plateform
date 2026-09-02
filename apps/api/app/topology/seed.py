from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import CloudAccountRow, CloudEnvironmentRow, CloudProviderRow, LiveScopeStateRow, PlatformRegionRow
from app.topology.loader import load_topology
from app.topology.models import environment_scope_id

logger = get_logger(__name__)


def seed_topology(session: Session) -> None:
    topology = load_topology()
    provider = session.get(CloudProviderRow, "AWS")
    if provider is None:
        provider = CloudProviderRow(id="AWS", name="AWS")
        session.add(provider)

    seen_regions: set[str] = set()
    for account in topology.accounts:
        region_id = f"aws-{account.logical_region.lower()}"
        if region_id not in seen_regions:
            region = session.get(PlatformRegionRow, region_id)
            if region is None:
                region = PlatformRegionRow(id=region_id, provider="AWS", name=account.logical_region)
                session.add(region)
            region.provider = "AWS"
            region.name = account.logical_region
            region.cloud_region = account.cloud_region
            seen_regions.add(region_id)

        row = session.get(CloudAccountRow, account.id)
        if row is None:
            row = CloudAccountRow(id=account.id)
            session.add(row)
        row.provider = account.provider
        row.platform_region = account.logical_region
        row.cloud_region = account.cloud_region
        row.alias = account.alias
        row.account_id = account.account_id or ""
        row.role_arn = account.role_arn or ""
        row.external_id = account.external_id or ""
        row.account_class = account.account_class
        row.readonly = account.readonly
        row.session_name = account.session_name
        row.cluster_environment_tag = account.cluster_environment_tag

        for environment in account.environments:
            env_id = environment_scope_id(account.alias, environment)
            env_row = session.get(CloudEnvironmentRow, env_id)
            if env_row is None:
                env_row = CloudEnvironmentRow(id=env_id, discovery_active=False)
                session.add(env_row)
            env_row.account_id = account.id
            env_row.provider = account.provider
            env_row.platform_region = account.logical_region
            env_row.cloud_region = account.cloud_region
            env_row.environment = environment
            env_row.account_alias = account.alias
            env_row.readonly = account.readonly or environment == "PRD"
            env_row.enabled = True

    _copy_legacy_emea_dev(session)
    session.flush()
    logger.info("Seeded AWS topology accounts=%s", len(topology.accounts))


def _copy_legacy_emea_dev(session: Session) -> None:
    legacy = session.get(LiveScopeStateRow, "aws-emea-dev")
    current = session.get(CloudEnvironmentRow, "aws-emea-nonprod-dev")
    if legacy is None or current is None:
        return
    if current.discovery_active:
        return
    if not legacy.discovery_active:
        return
    current.discovery_active = True
    current.last_discovery_at = legacy.last_discovery_at
    current.last_health_at = legacy.last_health_at
    current.last_certificate_scan_at = legacy.last_certificate_scan_at
    current.last_successful_scan_at = legacy.last_discovery_at or legacy.last_health_at
