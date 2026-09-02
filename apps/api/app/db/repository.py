from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    AcmCertificateRow,
    EksClusterHealthRow,
    EksClusterRow,
    LiveScopeStateRow,
    PlatformJobRow,
)
from app.providers.aws.models import ClusterHealthSnapshot, DiscoveredCertificate, DiscoveredCluster

LIVE_SCOPE_ID = "aws-emea-dev"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cluster_public_id(name: str, cloud_region: str) -> str:
    return f"eks-{cloud_region}-{name}"


def certificate_public_id(arn: str) -> str:
    suffix = arn.rsplit("/", 1)[-1]
    return f"acm-{suffix}"


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def scope_state(self) -> LiveScopeStateRow:
        row = self.session.get(LiveScopeStateRow, LIVE_SCOPE_ID)
        if row is None:
            row = LiveScopeStateRow(
                id=LIVE_SCOPE_ID,
                provider=settings.aws_provider,
                platform_region=settings.aws_platform_region,
                environment=settings.aws_environment,
                discovery_active=False,
            )
            self.session.add(row)
            self.session.flush()
        return row

    def discovery_is_live(self) -> bool:
        return bool(self.scope_state().discovery_active)

    def certificates_are_live(self) -> bool:
        return self.scope_state().last_certificate_scan_at is not None

    def replace_clusters(self, clusters: list[DiscoveredCluster]) -> list[EksClusterRow]:
        now = utcnow()
        seen_ids: set[str] = set()
        rows: list[EksClusterRow] = []
        for cluster in clusters:
            public_id = cluster_public_id(cluster.name, cluster.cloud_region)
            seen_ids.add(public_id)
            row = self.session.get(EksClusterRow, public_id)
            if row is None:
                row = EksClusterRow(id=public_id, arn=cluster.arn, name=cluster.name)
                self.session.add(row)
            row.arn = cluster.arn
            row.name = cluster.name
            row.cloud_region = cluster.cloud_region
            row.aws_account_id = cluster.aws_account_id
            row.account_alias = cluster.account_alias
            row.provider = "AWS"
            row.platform_region = cluster.platform_region
            row.environment = cluster.environment
            row.kubernetes_version = cluster.kubernetes_version
            row.endpoint_status = cluster.endpoint_status
            row.cluster_status = cluster.cluster_status
            row.platform_version = cluster.platform_version
            row.created_at = cluster.created_at
            row.last_seen_at = now
            row.present = True
            rows.append(row)
        existing = self.session.scalars(select(EksClusterRow)).all()
        for row in existing:
            if row.id not in seen_ids:
                row.present = False
        state = self.scope_state()
        state.discovery_active = True
        state.last_discovery_at = now
        self.session.flush()
        return rows

    def upsert_health(self, cluster_id: str, snapshot: ClusterHealthSnapshot) -> EksClusterHealthRow:
        row = self.session.get(EksClusterHealthRow, cluster_id)
        if row is None:
            row = EksClusterHealthRow(cluster_id=cluster_id)
            self.session.add(row)
        row.control_plane_status = snapshot.control_plane_status
        row.kubernetes_api_reachable = snapshot.kubernetes_api_reachable
        row.node_count = snapshot.node_count
        row.ready_node_count = snapshot.ready_node_count
        row.pod_count = snapshot.pod_count
        row.unhealthy_pod_count = snapshot.unhealthy_pod_count
        row.crashloop_backoff_count = snapshot.crashloop_backoff_count
        row.pending_pod_count = snapshot.pending_pod_count
        row.unavailable_deployment_count = snapshot.unavailable_deployment_count
        row.failed_job_count = snapshot.failed_job_count
        row.last_checked = snapshot.last_checked
        row.detail = snapshot.detail
        self.scope_state().last_health_at = snapshot.last_checked
        self.session.flush()
        return row

    def replace_certificates(self, certificates: list[DiscoveredCertificate]) -> list[AcmCertificateRow]:
        now = utcnow()
        seen: set[str] = set()
        rows: list[AcmCertificateRow] = []
        for item in certificates:
            public_id = certificate_public_id(item.arn)
            seen.add(public_id)
            row = self.session.get(AcmCertificateRow, public_id)
            if row is None:
                row = AcmCertificateRow(id=public_id, arn=item.arn, domain_name=item.domain_name)
                self.session.add(row)
            row.arn = item.arn
            row.domain_name = item.domain_name
            row.subject_alternative_names = json.dumps(item.subject_alternative_names)
            row.issuer = item.issuer
            row.status = item.status
            row.not_before = item.not_before
            row.not_after = item.not_after
            row.days_remaining = item.days_remaining
            row.in_use_by = json.dumps(item.in_use_by)
            row.renewal_eligibility = item.renewal_eligibility
            row.last_checked = item.last_checked
            row.provider = "AWS"
            row.platform_region = item.platform_region
            row.environment = item.environment
            row.account_alias = item.account_alias
            row.cloud_region = item.cloud_region
            row.present = True
            rows.append(row)
        for row in self.session.scalars(select(AcmCertificateRow)).all():
            if row.id not in seen:
                row.present = False
        self.scope_state().last_certificate_scan_at = now
        self.session.flush()
        return rows

    def present_clusters(self) -> list[EksClusterRow]:
        return list(self.session.scalars(select(EksClusterRow).where(EksClusterRow.present.is_(True))))

    def get_cluster(self, cluster_id: str) -> EksClusterRow | None:
        return self.session.get(EksClusterRow, cluster_id)

    def get_health(self, cluster_id: str) -> EksClusterHealthRow | None:
        return self.session.get(EksClusterHealthRow, cluster_id)

    def present_certificates(self) -> list[AcmCertificateRow]:
        return list(self.session.scalars(select(AcmCertificateRow).where(AcmCertificateRow.present.is_(True))))

    def find_running_job(self, kind: str) -> PlatformJobRow | None:
        return self.session.scalar(
            select(PlatformJobRow).where(PlatformJobRow.kind == kind, PlatformJobRow.status.in_(("queued", "running")))
        )

    def create_job(self, kind: str, name: str, correlation_id: str) -> PlatformJobRow:
        existing = self.find_running_job(kind)
        if existing:
            return existing
        row = PlatformJobRow(
            id=str(uuid4()),
            kind=kind,
            name=name,
            status="queued",
            detail="Queued",
            correlation_id=correlation_id,
            provider="AWS",
            platform_region=settings.aws_platform_region,
            environment=settings.aws_environment,
            created_at=utcnow(),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def mark_job_running(self, job_id: str) -> PlatformJobRow | None:
        row = self.session.get(PlatformJobRow, job_id)
        if row is None:
            return None
        row.status = "running"
        row.started_at = utcnow()
        row.detail = "Running"
        self.session.flush()
        return row

    def mark_job_finished(self, job_id: str, *, status: str, detail: str, error_class: str = "") -> None:
        row = self.session.get(PlatformJobRow, job_id)
        if row is None:
            return
        row.status = status
        row.detail = detail
        row.error_class = error_class
        row.finished_at = utcnow()
        self.session.flush()

    def list_jobs(self) -> list[PlatformJobRow]:
        return list(self.session.scalars(select(PlatformJobRow).order_by(PlatformJobRow.created_at.desc())))
