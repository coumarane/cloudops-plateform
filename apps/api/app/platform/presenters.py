from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerting.models import AlertStatus
from app.core.config import settings
from app.db.models import (
    AcmCertificateRow,
    AlertRow,
    ApplicationHealthRow,
    CloudAccountRow,
    CloudEnvironmentRow,
    EksClusterRow,
    ManagedApplicationRow,
    ManagedProviderRow,
    PlatformJobRow,
)
from app.db.repository import InventoryRepository
from app.domain.enums import ENVIRONMENTS, Environment, cloud_region as default_cloud_region, platform_for
from app.domain.models import (
    AccountRecord,
    ApplicationRecord,
    CellMetrics,
    ClusterRecord,
    EnvironmentIdentity,
    EnvironmentRecord,
    MatrixRow,
    ProviderRecord,
    RegionRecord,
    Scope,
)
from app.services.mappers import to_certificate_record, to_cluster_record, to_job_record
from app.topology.models import environment_slug


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def demo_mode() -> bool:
    return bool(settings.demo_mode)


def configured_provider_count(session: Session) -> int:
    return session.query(ManagedProviderRow).filter(ManagedProviderRow.enabled.is_(True)).count()


def data_source(session: Session) -> str:
    if demo_mode():
        return "DEMO"
    running = session.query(PlatformJobRow).filter(PlatformJobRow.status == "running").count()
    if running:
        return "SYNCING"
    last = session.query(CloudEnvironmentRow.last_successful_scan_at).order_by(CloudEnvironmentRow.last_successful_scan_at.desc()).limit(1).scalar()
    if last is not None:
        moment = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - moment
        if age.total_seconds() > 6 * 60 * 60:
            return "STALE"
    return "REAL"


def provider_dump(session: Session, row: ManagedProviderRow) -> dict:
    accounts = list(session.scalars(select(CloudAccountRow).where(CloudAccountRow.managed_provider_id == row.id)))
    env_count = 0
    cluster_count = 0
    last_sync = row.last_synchronized_at
    for account in accounts:
        envs = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == account.id)))
        env_count += len(envs)
        for env in envs:
            cluster_count += session.query(EksClusterRow).filter(
                EksClusterRow.environment_id == env.id,
                EksClusterRow.present.is_(True),
                EksClusterRow.ignored.is_(False),
            ).count()
            if env.last_successful_scan_at and (last_sync is None or env.last_successful_scan_at > last_sync):
                last_sync = env.last_successful_scan_at
    return {
        "id": row.id,
        "name": row.name,
        "providerType": row.provider_type,
        "provider": row.provider_type,
        "platform": {"AWS": "EKS", "Alibaba": "ACK", "Azure": "AKS", "GCP": "GKE"}.get(row.provider_type, "Kubernetes"),
        "description": row.description,
        "enabled": row.enabled,
        "authStrategy": row.auth_strategy,
        "status": row.status,
        "validationStatus": row.validation_status,
        "errorCategory": row.error_category,
        "identityAccount": row.identity_account,
        "identityPrincipal": row.identity_principal,
        "lastValidatedAt": _iso(row.last_validated_at),
        "lastSynchronizedAt": _iso(last_sync or row.last_synchronized_at),
        "accounts": len(accounts),
        "environments": env_count,
        "clusters": cluster_count,
        "regions": ["China"] if row.provider_type == "Alibaba" else ["AMER", "EMEA", "APAC"],
        "inventorySupported": row.provider_type not in {"Azure", "GCP"},
    }


def account_dump(session: Session, row: CloudAccountRow) -> dict:
    from app.platform.readiness import account_readiness

    envs = list(session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.account_id == row.id)))
    hosted = [item.environment for item in envs]
    clusters = session.query(EksClusterRow).filter(
        EksClusterRow.account_alias == row.alias,
        EksClusterRow.present.is_(True),
        EksClusterRow.ignored.is_(False),
    ).count()
    klass = "Production" if row.account_class.upper() in {"PROD", "PRODUCTION"} else "Non-production"
    primary_env = hosted[0] if hosted else "DEV"
    return {
        "id": row.id,
        "account": row.alias,
        "name": row.display_name or row.alias,
        "provider": row.provider,
        "region": row.platform_region,
        "environment": primary_env,
        "accountClass": klass,
        "accountClassCode": row.account_class,
        "cloudRegion": row.cloud_region,
        "platform": {"AWS": "EKS", "Alibaba": "ACK", "Azure": "AKS", "GCP": "GKE"}.get(row.provider, "Kubernetes"),
        "hostedEnvironments": hosted,
        "environments": ", ".join(hosted),
        "clusters": clusters,
        "awsAccountId": row.account_id,
        "accountId": row.account_id,
        "roleArn": row.role_arn,
        "ramRole": row.ram_role,
        "authStrategy": row.auth_strategy,
        "credentialRef": row.credential_ref,
        "enabled": row.enabled,
        "managedProviderId": row.managed_provider_id,
        "inventorySupported": row.provider not in {"Azure", "GCP"},
        "description": row.description,
        "validationStatus": row.validation_status,
        "lastValidatedAt": _iso(row.last_validated_at),
        "identityAccount": row.identity_account,
        "identityPrincipal": row.identity_principal,
        "readiness": account_readiness(row),
        "readonly": row.readonly,
    }


def environment_dump(session: Session, row: CloudEnvironmentRow) -> dict:
    from app.platform.readiness import environment_readiness

    account = session.get(CloudAccountRow, row.account_id)
    clusters = session.query(EksClusterRow).filter(
        EksClusterRow.environment_id == row.id,
        EksClusterRow.present.is_(True),
        EksClusterRow.ignored.is_(False),
    ).count()
    return {
        "id": row.id,
        "name": row.name or f"{row.provider} {row.platform_region} {row.environment}",
        "code": row.code or environment_slug(row.environment),
        "provider": row.provider,
        "region": row.platform_region,
        "environment": row.environment,
        "platform": {"AWS": "EKS", "Alibaba": "ACK", "Azure": "AKS", "GCP": "GKE"}.get(row.provider, "Kubernetes"),
        "cloudRegion": row.cloud_region,
        "account": row.account_alias,
        "accountId": row.account_id,
        "clusterName": "",
        "readonly": row.readonly,
        "source": {"AWS": "aws", "Alibaba": "alibaba", "Azure": "azure", "GCP": "gcp"}.get(row.provider, "unknown"),
        "lastSuccessfulScan": _iso(row.last_successful_scan_at),
        "lastError": row.last_error or None,
        "discoveryActive": row.discovery_active,
        "enabled": row.enabled,
        "description": row.description,
        "readiness": environment_readiness(row, account) if account else row.readiness_status,
        "clusters": clusters,
        "awsAccountId": account.account_id if account else None,
    }


def application_dump(session: Session, row: ManagedApplicationRow) -> dict:
    from app.db.models import ApplicationEnvironmentBindingRow

    bindings = list(
        session.scalars(select(ApplicationEnvironmentBindingRow).where(ApplicationEnvironmentBindingRow.application_id == row.id))
    )
    first = bindings[0] if bindings else None
    env = session.get(CloudEnvironmentRow, first.environment_id) if first else None
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "ownerTeam": row.owner_team,
        "repositoryId": row.repository_id,
        "pipelineId": row.pipeline_id,
        "enabled": row.enabled,
        "namespace": first.namespace if first else "",
        "replicas": "—",
        "issue": "Healthy",
        "provider": env.provider if env else "AWS",
        "region": env.platform_region if env else "EMEA",
        "environment": env.environment if env else "DEV",
        "cluster": first.cluster_id if first else "",
        "action": "Status",
        "bindings": [
            {
                "id": item.id,
                "environmentId": item.environment_id,
                "clusterId": item.cluster_id,
                "namespace": item.namespace,
                "workload": item.workload,
                "healthEndpoint": item.health_endpoint,
            }
            for item in bindings
        ],
    }


def identity_from_row(row: CloudEnvironmentRow) -> EnvironmentIdentity:
    return EnvironmentIdentity(
        id=row.id,
        readiness=row.readiness_status or None,
        provider=row.provider,  # type: ignore[arg-type]
        region=row.platform_region,  # type: ignore[arg-type]
        environment=row.environment,  # type: ignore[arg-type]
        platform=platform_for(row.provider),  # type: ignore[arg-type]
        cloudRegion=row.cloud_region,
        account=row.account_alias,
        clusterName="",
        readonly=row.readonly,
        source="alibaba" if row.provider == "Alibaba" else "aws",
        lastSuccessfulScan=_iso(row.last_successful_scan_at),
        lastError=row.last_error or None,
        discoveryActive=row.discovery_active,
        awsAccountId=None,
    )


def live_regions(session: Session, scope: Scope) -> list[RegionRecord]:
    seen: set[tuple[str, str]] = set()
    items: list[RegionRecord] = []
    managed_only = configured_provider_count(session) > 0 or not settings.seed_topology
    for row in session.scalars(select(CloudAccountRow).where(CloudAccountRow.enabled.is_(True))):
        if managed_only and not row.managed_provider_id:
            continue
        key = (row.provider, row.platform_region)
        if key in seen:
            continue
        seen.add(key)
        record = RegionRecord(
            id=f"{row.provider.lower()}-{row.platform_region.lower()}",
            name=row.platform_region,  # type: ignore[arg-type]
            provider=row.provider,  # type: ignore[arg-type]
            cloudRegion=row.cloud_region,
            platform=platform_for(row.provider),  # type: ignore[arg-type]
        )
        if scope.provider and record.provider != scope.provider:
            continue
        if scope.region and record.name != scope.region:
            continue
        items.append(record)
    return items


def live_accounts(session: Session, scope: Scope) -> list[AccountRecord]:
    items: list[AccountRecord] = []
    managed_only = configured_provider_count(session) > 0 or not settings.seed_topology
    for row in session.scalars(select(CloudAccountRow)):
        if managed_only and not row.managed_provider_id:
            continue
        payload = account_dump(session, row)
        record = AccountRecord(
            id=payload["id"],
            account=payload["account"],
            provider=payload["provider"],  # type: ignore[arg-type]
            region=payload["region"],  # type: ignore[arg-type]
            environment=payload["environment"],  # type: ignore[arg-type]
            accountClass=payload["accountClass"],  # type: ignore[arg-type]
            cloudRegion=payload["cloudRegion"],
            platform=payload["platform"],
            hostedEnvironments=payload["hostedEnvironments"],  # type: ignore[arg-type]
            environments=payload["environments"],
            clusters=payload["clusters"],
        )
        if scope.provider and record.provider != scope.provider:
            continue
        if scope.region and record.region != scope.region:
            continue
        if scope.account and record.account != scope.account:
            continue
        if scope.environment and scope.environment not in record.hostedEnvironments:
            continue
        items.append(record)
    return items


def live_environments(session: Session, scope: Scope) -> list[EnvironmentIdentity]:
    items: list[EnvironmentIdentity] = []
    managed_only = configured_provider_count(session) > 0 or not settings.seed_topology
    for row in session.scalars(select(CloudEnvironmentRow)):
        if managed_only:
            account = session.get(CloudAccountRow, row.account_id)
            if account is None or not account.managed_provider_id:
                continue
        identity = identity_from_row(row)
        if scope.provider and identity.provider != scope.provider:
            continue
        if scope.region and identity.region != scope.region:
            continue
        if scope.environment and identity.environment != scope.environment:
            continue
        if scope.account and identity.account != scope.account:
            continue
        items.append(identity)
    return items


def live_clusters(session: Session, scope: Scope) -> list[ClusterRecord]:
    repo = InventoryRepository(session)
    items: list[ClusterRecord] = []
    for cluster in repo.present_clusters():
        if cluster.ignored:
            continue
        record = to_cluster_record(cluster, repo.get_health(cluster.id))
        if scope.provider and record.provider != scope.provider:
            continue
        if scope.region and record.region != scope.region:
            continue
        if scope.environment and record.environment != scope.environment:
            continue
        if scope.account and record.account != scope.account:
            continue
        items.append(record)
    return items


def live_applications(session: Session, scope: Scope) -> list[ApplicationRecord]:
    items: list[ApplicationRecord] = []
    for row in session.scalars(select(ManagedApplicationRow).where(ManagedApplicationRow.enabled.is_(True))):
        payload = application_dump(session, row)
        record = ApplicationRecord(
            id=payload["id"],
            name=payload["name"],
            namespace=payload["namespace"] or "default",
            replicas=payload["replicas"],
            issue=payload["issue"],
            provider=payload["provider"],  # type: ignore[arg-type]
            region=payload["region"],  # type: ignore[arg-type]
            environment=payload["environment"],  # type: ignore[arg-type]
            cluster=payload["cluster"] or "—",
            repositoryId=payload["repositoryId"] or None,
            pipelineId=payload["pipelineId"] or None,
        )
        health = session.scalar(select(ApplicationHealthRow).where(ApplicationHealthRow.application_id == row.id))
        if health is not None:
            record = record.model_copy(update={"healthStatus": health.status, "healthSummary": health.summary})
        if scope.provider and record.provider != scope.provider:
            continue
        if scope.region and record.region != scope.region:
            continue
        if scope.environment and record.environment != scope.environment:
            continue
        items.append(record)
    return items


def live_certificates(session: Session, scope: Scope):
    repo = InventoryRepository(session)
    items = []
    for row in repo.present_certificates():
        record = to_certificate_record(row)
        if scope.provider and record.provider != scope.provider:
            continue
        if scope.region and record.region != scope.region:
            continue
        if scope.environment and record.environment != scope.environment:
            continue
        items.append(record)
    return items


def live_jobs(session: Session, scope: Scope):
    items = []
    for row in session.scalars(select(PlatformJobRow).order_by(PlatformJobRow.created_at.desc())):
        record = to_job_record(row)
        if scope.provider and record.provider != scope.provider:
            continue
        if scope.region and record.region != scope.region:
            continue
        if scope.environment and record.environment != scope.environment:
            continue
        items.append(record)
    return items


def empty_cell() -> CellMetrics:
    return CellMetrics()


def live_matrix(session: Session, scope: Scope) -> list[MatrixRow]:
    by_key: dict[tuple[str, str], MatrixRow] = {}
    managed_only = configured_provider_count(session) > 0 or not settings.seed_topology
    for env in session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.enabled.is_(True))):
        if managed_only:
            account = session.get(CloudAccountRow, env.account_id)
            if account is None or not account.managed_provider_id:
                continue
        if scope.provider and env.provider != scope.provider:
            continue
        if scope.region and env.platform_region != scope.region:
            continue
        key = (env.provider, env.platform_region)
        if key not in by_key:
            cells = {item: empty_cell() for item in ENVIRONMENTS}
            by_key[key] = MatrixRow(
                provider=env.provider,  # type: ignore[arg-type]
                platform=platform_for(env.provider),  # type: ignore[arg-type]
                region=env.platform_region,  # type: ignore[arg-type]
                cells=cells,
            )
        if env.environment not in ENVIRONMENTS:
            continue
        clusters = live_clusters(
            session,
            Scope(provider=env.provider, region=env.platform_region, environment=env.environment),  # type: ignore[arg-type]
        )
        cell = by_key[key].cells[env.environment]  # type: ignore[index]
        cell.clustersHealthy = sum(1 for item in clusters if item.status == "Healthy")
        cell.clustersDegraded = sum(1 for item in clusters if item.status == "Degraded")
        cell.clustersUnreachable = sum(1 for item in clusters if item.status == "Unreachable")
        cell.live = env.discovery_active
        cell.lastError = env.last_error or None
        cell.readonly = env.readonly
        alerts = session.query(AlertRow).filter(
            AlertRow.environment == env.environment,
            AlertRow.provider == env.provider,
            AlertRow.status.in_((AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)),
        ).count()
        cell.openAlerts = alerts
    rows = list(by_key.values())
    if scope.environment:
        for row in rows:
            for environment in ENVIRONMENTS:
                if environment != scope.environment:
                    row.cells[environment] = empty_cell()
    return rows
