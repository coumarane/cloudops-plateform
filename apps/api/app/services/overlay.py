from __future__ import annotations

from app.core.logging import get_logger
from app.db.models import CloudEnvironmentRow
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.domain.models import (
    CertificateRecord,
    ClusterRecord,
    EnvironmentCertificate,
    EnvironmentIdentity,
    EnvironmentRecord,
    MatrixRow,
    RunRecord,
)
from app.services.mappers import to_certificate_record, to_cluster_record, to_health_record, to_job_record
from app.topology.models import environment_slug

logger = get_logger(__name__)


def _scope_key(row: CloudEnvironmentRow) -> tuple[str, str, str]:
    return (row.provider, row.platform_region, row.environment)


def _identity_from_row(identity: EnvironmentIdentity, row: CloudEnvironmentRow) -> EnvironmentIdentity:
        source = identity.source
        if row.discovery_active:
            source = "alibaba" if row.provider == "Alibaba" else "aws"
        return identity.model_copy(
            update={
                "account": row.account_alias,
                "cloudRegion": row.cloud_region,
                "readonly": row.readonly,
                "source": source,
                "lastSuccessfulScan": row.last_successful_scan_at.isoformat() if row.last_successful_scan_at else None,
                "lastError": row.last_error or None,
                "discoveryActive": row.discovery_active,
                "awsAccountId": None,
            }
        )


def overlay_environment_identities(items: list[EnvironmentIdentity]) -> list[EnvironmentIdentity]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        by_key = {_scope_key(row): row for row in repo.list_environment_rows()}
        updated: list[EnvironmentIdentity] = []
        for item in items:
            row = by_key.get((item.provider, item.region, item.environment))
            updated.append(_identity_from_row(item, row) if row else item)
        return updated
    except Exception:
        logger.exception("Environment identity overlay unavailable")
        return items
    finally:
        session.close()


def overlay_clusters(items: list[ClusterRecord]) -> list[ClusterRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        live_scopes = repo.live_discovery_scopes()
        if not live_scopes:
            return items
        live = [
            to_cluster_record(cluster, repo.get_health(cluster.id))
            for cluster in repo.present_clusters()
            if (cluster.provider, cluster.platform_region, cluster.environment) in live_scopes
        ]
        kept = [item for item in items if (item.provider, item.region, item.environment) not in live_scopes]
        return kept + live
    except Exception:
        logger.exception("Live cluster overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def overlay_certificates(items: list[CertificateRecord]) -> list[CertificateRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        live_scopes = repo.live_certificate_scopes()
        if not live_scopes:
            return items
        env_rows = repo.list_environment_rows()
        envs_by_account: dict[str, list[CloudEnvironmentRow]] = {}
        for row in env_rows:
            envs_by_account.setdefault(row.account_alias, []).append(row)
        live: list[CertificateRecord] = []
        for row in repo.present_certificates():
            record = to_certificate_record(row)
            targets = envs_by_account.get(row.account_alias, [])
            if row.environment:
                targets = [item for item in targets if item.environment == row.environment]
            for env in targets:
                if (env.provider, env.platform_region, env.environment) not in live_scopes:
                    continue
                copied = record.model_copy(
                    update={
                        "environment": env.environment,
                        "region": env.platform_region,
                        "id": f"{record.id}-{environment_slug(env.environment)}" if len(targets) > 1 else record.id,
                    }
                )
                live.append(copied)
        kept = [item for item in items if (item.provider, item.region, item.environment) not in live_scopes]
        return kept + live
    except Exception:
        logger.exception("Live certificate overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def overlay_jobs(items: list[RunRecord]) -> list[RunRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        live = [to_job_record(row) for row in repo.list_jobs()]
        return live + items
    except Exception:
        logger.exception("Live job overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def overlay_environment(record: EnvironmentRecord | None) -> EnvironmentRecord | None:
    if record is None:
        return record
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        env_row = repo.environment_row(record.identity.provider, record.identity.region, record.identity.environment)
        if env_row is None:
            return record
        updated = record.model_copy(deep=True)
        updated.identity = _identity_from_row(record.identity, env_row)
        if env_row.discovery_active:
            updated.clusters = [
                to_cluster_record(cluster, repo.get_health(cluster.id))
                for cluster in repo.present_clusters_for(env_row.platform_region, env_row.environment)
                if cluster.provider == env_row.provider
            ]
        if env_row.last_certificate_scan_at is not None:
            certs = [
                to_certificate_record(row)
                for row in repo.present_certificates_for_account(env_row.account_alias)
                if not row.environment or row.environment == env_row.environment
            ]
            if certs:
                updated.certificates = [
                    EnvironmentCertificate(name=item.domain, daysToExpiry=item.daysRemaining) for item in certs
                ]
        return updated
    except Exception:
        logger.exception("Live environment overlay unavailable; using mock data")
        return record
    finally:
        session.close()


def overlay_matrix(rows: list[MatrixRow]) -> list[MatrixRow]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        env_rows = repo.list_environment_rows()
        if not env_rows:
            return rows
        live_clusters = repo.present_clusters()
        health_by_scope: dict[tuple[str, str, str], list] = {}
        for cluster in live_clusters:
            key = (cluster.provider, cluster.platform_region, cluster.environment)
            health_by_scope.setdefault(key, []).append(cluster)
        certs_by_account = {}
        for cert in repo.present_certificates():
            certs_by_account.setdefault(cert.account_alias, []).append(cert)
        env_by_key = {_scope_key(row): row for row in env_rows}
        patched: list[MatrixRow] = []
        for row in rows:
            cells = dict(row.cells)
            changed = False
            for environment, current in cells.items():
                env_row = env_by_key.get((row.provider, row.region, environment))
                if env_row is None:
                    continue
                next_cell = current
                if env_row.discovery_active:
                    scoped = health_by_scope.get((row.provider, row.region, environment), [])
                    healthy = degraded = unreachable = 0
                    for cluster in scoped:
                        status = to_cluster_record(cluster, repo.get_health(cluster.id)).status
                        if status == "Unreachable":
                            unreachable += 1
                        elif status == "Degraded":
                            degraded += 1
                        else:
                            healthy += 1
                    next_cell = next_cell.model_copy(
                        update={
                            "clustersHealthy": healthy,
                            "clustersDegraded": degraded,
                            "clustersUnreachable": unreachable,
                            "live": True,
                        }
                    )
                    changed = True
                if env_row.last_certificate_scan_at is not None:
                    certs = certs_by_account.get(env_row.account_alias, [])
                    expiring = [
                        item
                        for item in certs
                        if item.days_remaining is not None
                        and 0 <= item.days_remaining <= 14
                        and (not item.environment or item.environment == environment)
                    ]
                    next_cert = min(
                        (item.days_remaining for item in expiring if item.days_remaining is not None),
                        default=current.nextCertExpiryDays,
                    )
                    next_cell = next_cell.model_copy(
                        update={
                            "certsExpiring14d": len(expiring),
                            "nextCertExpiryDays": next_cert,
                            "live": True,
                        }
                    )
                    changed = True
                if env_row.last_error or env_row.readonly:
                    next_cell = next_cell.model_copy(
                        update={"lastError": env_row.last_error or None, "readonly": env_row.readonly}
                    )
                    changed = True
                cells[environment] = next_cell
            patched.append(
                MatrixRow(provider=row.provider, platform=row.platform, region=row.region, cells=cells)
                if changed
                else row
            )
        return patched
    except Exception:
        logger.exception("Live dashboard overlay unavailable; using mock data")
        return rows
    finally:
        session.close()


def load_cluster_detail(cluster_id: str):
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        cluster = repo.get_cluster(cluster_id)
        if cluster is None or not cluster.present:
            return None, None
        health = repo.get_health(cluster_id)
        health_record = to_health_record(cluster, health) if health else None
        return to_cluster_record(cluster, health), health_record
    except Exception:
        logger.exception("Live cluster detail unavailable")
        return None, None
    finally:
        session.close()
