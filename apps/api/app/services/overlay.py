from __future__ import annotations

from app.core.config import settings
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.domain.enums import Environment, Provider, Region
from app.domain.models import (
    CellMetrics,
    CertificateRecord,
    ClusterRecord,
    EnvironmentCertificate,
    EnvironmentRecord,
    MatrixRow,
    RunRecord,
)
from app.services.mappers import to_certificate_record, to_cluster_record, to_health_record, to_job_record

LIVE_PROVIDER: Provider = "AWS"
LIVE_REGION: Region = "EMEA"
LIVE_ENVIRONMENT: Environment = "DEV"


def is_live_cell(provider: str, region: str, environment: str) -> bool:
    return (provider, region, environment) == (LIVE_PROVIDER, LIVE_REGION, LIVE_ENVIRONMENT)


def overlay_clusters(items: list[ClusterRecord]) -> list[ClusterRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        if not repo.discovery_is_live():
            return items
        live = [
            to_cluster_record(cluster, repo.get_health(cluster.id))
            for cluster in repo.present_clusters()
        ]
        kept = [item for item in items if not is_live_cell(item.provider, item.region, item.environment)]
        return kept + live
    finally:
        session.close()


def overlay_certificates(items: list[CertificateRecord]) -> list[CertificateRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        if not repo.certificates_are_live():
            return items
        live = [to_certificate_record(row) for row in repo.present_certificates()]
        kept = [item for item in items if not is_live_cell(item.provider, item.region, item.environment)]
        return kept + live
    finally:
        session.close()


def overlay_jobs(items: list[RunRecord]) -> list[RunRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        live = [to_job_record(row) for row in repo.list_jobs()]
        return live + items
    finally:
        session.close()


def overlay_environment(record: EnvironmentRecord | None) -> EnvironmentRecord | None:
    if record is None or not is_live_cell(record.identity.provider, record.identity.region, record.identity.environment):
        return record
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        if not repo.discovery_is_live():
            return record
        live_clusters = [
            to_cluster_record(cluster, repo.get_health(cluster.id))
            for cluster in repo.present_clusters()
        ]
        live_certs = [to_certificate_record(row) for row in repo.present_certificates()] if repo.certificates_are_live() else []
        updated = record.model_copy(deep=True)
        updated.clusters = live_clusters
        if live_certs:
            updated.certificates = [
                EnvironmentCertificate(name=item.domain, daysToExpiry=item.daysRemaining) for item in live_certs
            ]
        return updated
    finally:
        session.close()


def overlay_matrix(rows: list[MatrixRow]) -> list[MatrixRow]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        if not repo.discovery_is_live():
            return rows
        live_clusters = repo.present_clusters()
        healthy = degraded = unreachable = 0
        for cluster in live_clusters:
            status = to_cluster_record(cluster, repo.get_health(cluster.id)).status
            if status == "Unreachable":
                unreachable += 1
            elif status == "Degraded":
                degraded += 1
            else:
                healthy += 1
        certs = repo.present_certificates() if repo.certificates_are_live() else []
        expiring = [item for item in certs if item.days_remaining is not None and 0 <= item.days_remaining <= 14]
        patched: list[MatrixRow] = []
        for row in rows:
            if row.provider != LIVE_PROVIDER or row.region != LIVE_REGION:
                patched.append(row)
                continue
            cells = dict(row.cells)
            current = cells[LIVE_ENVIRONMENT]
            next_cert = min(
                (item.days_remaining for item in expiring if item.days_remaining is not None),
                default=current.nextCertExpiryDays,
            )
            cells[LIVE_ENVIRONMENT] = CellMetrics(
                clustersHealthy=healthy,
                clustersDegraded=degraded,
                clustersUnreachable=unreachable,
                appsHealthy=current.appsHealthy,
                appsDegraded=current.appsDegraded,
                certsExpiring14d=len(expiring) if repo.certificates_are_live() else current.certsExpiring14d,
                nextCertExpiryDays=next_cert,
                secretsOverdue=current.secretsOverdue,
                secretsDueSoon=current.secretsDueSoon,
                nextSecretDueDays=current.nextSecretDueDays,
                failedDeploys=current.failedDeploys,
                githubFailures=current.githubFailures,
                pipelineFailures=current.pipelineFailures,
                openAlerts=current.openAlerts,
            )
            patched.append(MatrixRow(provider=row.provider, platform=row.platform, region=row.region, cells=cells))
        return patched
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
    finally:
        session.close()
