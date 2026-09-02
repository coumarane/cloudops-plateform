from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import sanitize_text
from app.db.models import (
    AcmCertificateRow,
    CloudEnvironmentRow,
    EksClusterHealthRow,
    EksClusterRow,
    PlatformJobRow,
)
from app.providers.common.models import ClusterHealthSnapshot, DiscoveredCertificate, DiscoveredCluster
from app.topology.models import environment_scope_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cluster_public_id(name: str, cloud_region: str, account_id: str, provider: str = "AWS") -> str:
    account = account_id or "unknown"
    prefix = "ack" if provider == "Alibaba" else "eks"
    return f"{prefix}-{cloud_region}-{account}-{name}"


def certificate_public_id(arn: str) -> str:
    suffix = arn.rsplit("/", 1)[-1]
    return f"acm-{suffix}"


class InventoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def environment_row(self, provider: str, platform_region: str, environment: str) -> CloudEnvironmentRow | None:
        return self.session.scalar(
            select(CloudEnvironmentRow).where(
                CloudEnvironmentRow.provider == provider,
                CloudEnvironmentRow.platform_region == platform_region,
                CloudEnvironmentRow.environment == environment,
            )
        )

    def environment_by_id(self, environment_id: str) -> CloudEnvironmentRow | None:
        return self.session.get(CloudEnvironmentRow, environment_id)

    def list_environment_rows(self) -> list[CloudEnvironmentRow]:
        return list(self.session.scalars(select(CloudEnvironmentRow)))

    def live_discovery_scopes(self) -> set[tuple[str, str, str]]:
        rows = self.session.scalars(select(CloudEnvironmentRow).where(CloudEnvironmentRow.discovery_active.is_(True)))
        return {(row.provider, row.platform_region, row.environment) for row in rows}

    def live_certificate_scopes(self) -> set[tuple[str, str, str]]:
        rows = self.session.scalars(
            select(CloudEnvironmentRow).where(CloudEnvironmentRow.last_certificate_scan_at.is_not(None))
        )
        return {(row.provider, row.platform_region, row.environment) for row in rows}

    def mark_scope_success(self, environment_id: str, kind: str) -> None:
        row = self.session.get(CloudEnvironmentRow, environment_id)
        if row is None:
            return
        now = utcnow()
        row.last_error = ""
        row.last_error_class = ""
        row.last_successful_scan_at = now
        if kind == "discovery":
            row.discovery_active = True
            row.last_discovery_at = now
        elif kind == "health":
            row.last_health_at = now
        elif kind == "certificates":
            row.last_certificate_scan_at = now
        self.session.flush()

    def mark_scope_error(self, environment_id: str, error: Exception) -> None:
        row = self.session.get(CloudEnvironmentRow, environment_id)
        if row is None:
            return
        row.last_error = sanitize_text(str(error))
        row.last_error_class = error.__class__.__name__
        row.last_error_at = utcnow()
        self.session.flush()

    def replace_clusters_for_scope(
        self,
        clusters: list[DiscoveredCluster],
        *,
        platform_region: str,
        environment: str,
        provider: str | None = None,
    ) -> list[EksClusterRow]:
        now = utcnow()
        seen_ids: set[str] = set()
        rows: list[EksClusterRow] = []
        resolved_provider = provider or (clusters[0].provider if clusters else "AWS")
        if clusters:
            environment_id = clusters[0].environment_id or environment_scope_id(
                clusters[0].account_alias, environment
            )
        else:
            environment_id = environment_scope_id("", environment)
        for cluster in clusters:
            public_id = cluster_public_id(
                cluster.name, cluster.cloud_region, cluster.aws_account_id, cluster.provider
            )
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
            row.provider = cluster.provider or resolved_provider
            row.platform_region = cluster.platform_region
            row.environment = cluster.environment
            row.kubernetes_version = cluster.kubernetes_version
            row.endpoint_status = cluster.endpoint_status
            row.cluster_status = cluster.cluster_status
            row.platform_version = cluster.platform_version
            row.created_at = cluster.created_at
            row.last_seen_at = now
            row.present = True
            row.environment_id = cluster.environment_id or environment_id
            row.cluster_type = cluster.cluster_type
            row.extra_json = cluster.extra_json or "{}"
            rows.append(row)
        existing = self.session.scalars(
            select(EksClusterRow).where(
                EksClusterRow.provider == resolved_provider,
                EksClusterRow.platform_region == platform_region,
                EksClusterRow.environment == environment,
            )
        ).all()
        for row in existing:
            if row.id not in seen_ids:
                row.present = False
        self.session.flush()
        return rows

    def replace_clusters(self, clusters: list[DiscoveredCluster]) -> list[EksClusterRow]:
        grouped: dict[tuple[str, str], list[DiscoveredCluster]] = {}
        for cluster in clusters:
            grouped.setdefault((cluster.platform_region, cluster.environment), []).append(cluster)
        rows: list[EksClusterRow] = []
        for (platform_region, environment), items in grouped.items():
            rows.extend(
                self.replace_clusters_for_scope(
                    items,
                    platform_region=platform_region,
                    environment=environment,
                    provider=items[0].provider,
                )
            )
            env_id = items[0].environment_id or environment_scope_id(items[0].account_alias, environment)
            self.mark_scope_success(env_id, "discovery")
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
        row.stateful_set_unhealthy_count = snapshot.stateful_set_unhealthy_count
        row.ingress_unhealthy_count = snapshot.ingress_unhealthy_count
        row.last_checked = snapshot.last_checked
        row.detail = snapshot.detail
        cluster = self.session.get(EksClusterRow, cluster_id)
        if cluster and cluster.environment_id:
            self.mark_scope_success(cluster.environment_id, "health")
        self.session.flush()
        return row

    def replace_certificates_for_account(
        self,
        certificates: list[DiscoveredCertificate],
        *,
        account_alias: str,
        platform_region: str,
    ) -> list[AcmCertificateRow]:
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
            row.provider = item.provider or "AWS"
            row.platform_region = item.platform_region
            row.environment = item.environment
            row.account_alias = item.account_alias
            row.cloud_region = item.cloud_region
            row.present = True
            row.cluster_name = item.cluster_name
            row.namespace = item.namespace
            row.source = item.source or ("acm" if item.provider == "AWS" else "")
            rows.append(row)
        for row in self.session.scalars(
            select(AcmCertificateRow).where(AcmCertificateRow.account_alias == account_alias)
        ).all():
            if row.id not in seen:
                row.present = False
        for env in self.session.scalars(
            select(CloudEnvironmentRow).where(
                CloudEnvironmentRow.account_alias == account_alias,
                CloudEnvironmentRow.platform_region == platform_region,
            )
        ):
            self.mark_scope_success(env.id, "certificates")
        self.session.flush()
        return rows

    def replace_certificates(self, certificates: list[DiscoveredCertificate]) -> list[AcmCertificateRow]:
        grouped: dict[tuple[str, str], list[DiscoveredCertificate]] = {}
        for item in certificates:
            grouped.setdefault((item.account_alias, item.platform_region), []).append(item)
        rows: list[AcmCertificateRow] = []
        for (alias, region), items in grouped.items():
            rows.extend(self.replace_certificates_for_account(items, account_alias=alias, platform_region=region))
        return rows

    def present_clusters(self) -> list[EksClusterRow]:
        return list(self.session.scalars(select(EksClusterRow).where(EksClusterRow.present.is_(True))))

    def present_clusters_for(self, platform_region: str, environment: str) -> list[EksClusterRow]:
        return list(
            self.session.scalars(
                select(EksClusterRow).where(
                    EksClusterRow.present.is_(True),
                    EksClusterRow.platform_region == platform_region,
                    EksClusterRow.environment == environment,
                )
            )
        )

    def get_cluster(self, cluster_id: str) -> EksClusterRow | None:
        return self.session.get(EksClusterRow, cluster_id)

    def get_health(self, cluster_id: str) -> EksClusterHealthRow | None:
        return self.session.get(EksClusterHealthRow, cluster_id)

    def present_certificates(self) -> list[AcmCertificateRow]:
        return list(self.session.scalars(select(AcmCertificateRow).where(AcmCertificateRow.present.is_(True))))

    def present_certificates_for_account(self, account_alias: str) -> list[AcmCertificateRow]:
        return list(
            self.session.scalars(
                select(AcmCertificateRow).where(
                    AcmCertificateRow.present.is_(True),
                    AcmCertificateRow.account_alias == account_alias,
                )
            )
        )

    def find_running_job(self, kind: str, *, target_id: str = "") -> PlatformJobRow | None:
        return self.session.scalar(
            select(PlatformJobRow).where(
                PlatformJobRow.kind == kind,
                PlatformJobRow.status.in_(("queued", "running")),
                PlatformJobRow.target_id == target_id,
            )
        )

    def create_job(
        self,
        kind: str,
        name: str,
        correlation_id: str,
        *,
        provider: str = "AWS",
        target_id: str = "",
        platform_region: str | None = None,
        environment: str | None = None,
    ) -> PlatformJobRow:
        existing = self.find_running_job(kind, target_id=target_id)
        if existing:
            return existing
        row = PlatformJobRow(
            id=str(uuid4()),
            kind=kind,
            name=name,
            status="queued",
            detail="Queued",
            correlation_id=correlation_id,
            provider=provider,
            platform_region=platform_region or ("China" if provider == "Alibaba" else "AMER"),
            environment=environment or "DEV",
            created_at=utcnow(),
            target_id=target_id,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def mark_account_validated(self, account_id: str, *, fingerprint: str, status: str) -> None:
        from app.db.models import CloudAccountRow

        row = self.session.get(CloudAccountRow, account_id)
        if row is None:
            return
        row.credential_fingerprint = fingerprint
        row.validation_status = status
        row.last_validated_at = utcnow()
        self.session.flush()

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
