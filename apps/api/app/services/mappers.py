from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.models import AcmCertificateRow, EksClusterHealthRow, EksClusterRow, PlatformJobRow
from app.domain.models import CertificateRecord, ClusterHealthRecord, ClusterRecord, RunRecord
from app.providers.common.models import ClusterHealthSnapshot, DiscoveredCluster


def _age(moment: datetime | None) -> str:
    if moment is None:
        return "—"
    now = datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    seconds = int((now - moment).total_seconds())
    if seconds < 60:
        return f"{max(seconds, 0)}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def catalog_status(cluster: EksClusterRow, health: EksClusterHealthRow | None) -> str:
    if cluster.cluster_status not in {"ACTIVE"}:
        return "Unreachable"
    if health is None:
        return "Degraded" if cluster.cluster_status != "ACTIVE" else "Healthy"
    if not health.kubernetes_api_reachable:
        return "Unreachable"
    if (
        health.crashloop_backoff_count
        or health.unavailable_deployment_count
        or health.failed_job_count
        or health.pending_pod_count
        or health.ready_node_count < health.node_count
    ):
        return "Degraded"
    return "Healthy"


def apps_label(health: EksClusterHealthRow | None) -> str:
    if health is None:
        return "Health pending"
    if not health.kubernetes_api_reachable:
        return "API unreachable"
    return f"{health.unhealthy_pod_count} unhealthy / {health.pod_count} pods"


def to_cluster_record(cluster: EksClusterRow, health: EksClusterHealthRow | None = None) -> ClusterRecord:
    return ClusterRecord(
        id=cluster.id,
        name=cluster.name,
        platform="ACK" if cluster.provider == "Alibaba" else "EKS",
        version=cluster.kubernetes_version or "—",
        nodes=health.ready_node_count if health else 0,
        provider=cluster.provider,  # type: ignore[arg-type]
        region=cluster.platform_region,  # type: ignore[arg-type]
        environment=cluster.environment,  # type: ignore[arg-type]
        account=cluster.account_alias,
        status=catalog_status(cluster, health),  # type: ignore[arg-type]
        appsLabel=apps_label(health),
        source="alibaba" if cluster.provider == "Alibaba" else "aws",
        awsAccountId=cluster.aws_account_id,
        cloudRegion=cluster.cloud_region,
        endpointStatus=cluster.endpoint_status,
        clusterStatus=cluster.cluster_status,
        platformVersion=cluster.platform_version,
        createdAt=cluster.created_at.isoformat() if cluster.created_at else None,
        lastChecked=health.last_checked.isoformat() if health else cluster.last_seen_at.isoformat(),
        ignored=bool(getattr(cluster, "ignored", False)),
        monitoringEnabled=bool(getattr(cluster, "monitoring_enabled", True)),
        externalClusterId=cluster.arn,
    )


def to_health_record(cluster: EksClusterRow, health: EksClusterHealthRow) -> ClusterHealthRecord:
    return ClusterHealthRecord(
        clusterId=cluster.id,
        clusterName=cluster.name,
        controlPlaneStatus=health.control_plane_status,
        kubernetesApiReachable=health.kubernetes_api_reachable,
        nodeCount=health.node_count,
        readyNodeCount=health.ready_node_count,
        podCount=health.pod_count,
        unhealthyPodCount=health.unhealthy_pod_count,
        crashLoopBackOffCount=health.crashloop_backoff_count,
        pendingPodCount=health.pending_pod_count,
        unavailableDeploymentCount=health.unavailable_deployment_count,
        failedJobCount=health.failed_job_count,
        statefulSetUnhealthyCount=health.stateful_set_unhealthy_count,
        ingressUnhealthyCount=health.ingress_unhealthy_count,
        lastChecked=health.last_checked.isoformat(),
        detail=health.detail,
        status=catalog_status(cluster, health),  # type: ignore[arg-type]
    )


def _renewal_status(row: AcmCertificateRow) -> str:
    from app.providers.common.certificates import catalog_renewal_status

    if "PENDING" in (row.renewal_eligibility or "").upper():
        return catalog_renewal_status(row.days_remaining, pending=True)
    return catalog_renewal_status(row.days_remaining)


def _source_label(row: AcmCertificateRow) -> str:
    if row.source:
        return row.source
    if row.provider == "Alibaba":
        return "cas"
    return "acm"


def to_certificate_record(row: AcmCertificateRow, *, alert_status: str | None = None) -> CertificateRecord:
    from app.providers.common.certificates import classify_expiry

    sans = json.loads(row.subject_alternative_names or "[]")
    in_use = json.loads(row.in_use_by or "[]")
    expires = row.not_after.date().isoformat() if row.not_after else ""
    expiry = row.expiry_status or classify_expiry(row.days_remaining)
    return CertificateRecord(
        id=row.id,
        name=row.domain_name,
        domain=row.domain_name,
        provider=row.provider,  # type: ignore[arg-type]
        region=row.platform_region,  # type: ignore[arg-type]
        environment=(row.environment or "DEV"),  # type: ignore[arg-type]
        cluster=row.cluster_name or ("acm" if row.provider == "AWS" else "cas"),
        namespace=row.namespace or ("acm" if row.provider == "AWS" else "cas"),
        issuer=row.issuer or ("ACM" if row.provider == "AWS" else "CAS"),
        expiresOn=expires,
        daysRemaining=row.days_remaining if row.days_remaining is not None else 0,
        renewalStatus=_renewal_status(row),  # type: ignore[arg-type]
        source=_source_label(row),
        arn=row.arn,
        subjectAlternativeNames=sans,
        status=row.status,
        notBefore=row.not_before.isoformat() if row.not_before else None,
        notAfter=row.not_after.isoformat() if row.not_after else None,
        inUseBy=in_use,
        renewalEligibility=row.renewal_eligibility,
        lastChecked=row.last_checked.isoformat() if row.last_checked else None,
        account=row.account_alias,
        expiryStatus=expiry,
        alertStatus=alert_status,
        serialNumber=row.serial_number or None,
        autoRenew=row.auto_renew,
        discoveryStatus=row.discovery_status or None,
        lastSeenAt=row.last_seen_at.isoformat() if row.last_seen_at else None,
        firstSeenAt=row.first_seen_at.isoformat() if row.first_seen_at else None,
        clusterId=row.cluster_id or None,
        applicationId=row.application_id or None,
        handshakeOk=row.handshake_ok,
        handshakeLatencyMs=row.handshake_latency_ms or None,
    )


def annotate_certificate(record: CertificateRecord) -> CertificateRecord:
    from app.providers.common.certificates import classify_expiry

    if record.expiryStatus:
        return record
    return record.model_copy(update={"expiryStatus": classify_expiry(record.daysRemaining)})


def to_job_record(row: PlatformJobRow) -> RunRecord:
    status_map = {"queued": "Running", "running": "Running", "succeeded": "Succeeded", "failed": "Failed"}
    alibaba = row.provider == "Alibaba"
    return RunRecord(
        id=row.id,
        name=row.name,
        detail=row.detail,
        result=status_map.get(row.status, "Running"),  # type: ignore[arg-type]
        age=_age(row.finished_at or row.started_at or row.created_at),
        provider="Alibaba" if alibaba else "AWS",
        region=row.platform_region,  # type: ignore[arg-type]
        environment=row.environment,  # type: ignore[arg-type]
        cluster="alibaba-fleet" if alibaba else "aws-fleet",
        source="alibaba" if alibaba else "aws",
        kind=row.kind,
        correlationId=row.correlation_id,
        jobStatus=row.status,
    )


def discovered_from_row(row: EksClusterRow) -> DiscoveredCluster:
    return DiscoveredCluster(
        name=row.name,
        arn=row.arn,
        cloud_region=row.cloud_region,
        aws_account_id=row.aws_account_id,
        kubernetes_version=row.kubernetes_version,
        endpoint_status=row.endpoint_status,
        cluster_status=row.cluster_status,
        platform_version=row.platform_version,
        created_at=row.created_at,
        environment=row.environment,
        platform_region=row.platform_region,
        account_alias=row.account_alias,
        environment_id=row.environment_id,
        provider=row.provider,
        cluster_type=row.cluster_type,
        extra_json=row.extra_json or "{}",
    )


def snapshot_from_health(row: EksClusterHealthRow) -> ClusterHealthSnapshot:
    return ClusterHealthSnapshot(
        cluster_arn=row.cluster_id,
        control_plane_status=row.control_plane_status,
        kubernetes_api_reachable=row.kubernetes_api_reachable,
        node_count=row.node_count,
        ready_node_count=row.ready_node_count,
        pod_count=row.pod_count,
        unhealthy_pod_count=row.unhealthy_pod_count,
        crashloop_backoff_count=row.crashloop_backoff_count,
        pending_pod_count=row.pending_pod_count,
        unavailable_deployment_count=row.unavailable_deployment_count,
        failed_job_count=row.failed_job_count,
        stateful_set_unhealthy_count=row.stateful_set_unhealthy_count,
        ingress_unhealthy_count=row.ingress_unhealthy_count,
        last_checked=row.last_checked,
        detail=row.detail,
    )
