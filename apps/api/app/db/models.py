from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EksClusterRow(Base):
    __tablename__ = "eks_clusters"
    __table_args__ = (UniqueConstraint("arn", name="uq_eks_clusters_arn"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    arn: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cloud_region: Mapped[str] = mapped_column(String(64), nullable=False)
    aws_account_id: Mapped[str] = mapped_column(String(32), nullable=False)
    account_alias: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="AWS")
    platform_region: Mapped[str] = mapped_column(String(32), default="EMEA")
    environment: Mapped[str] = mapped_column(String(32), default="DEV")
    kubernetes_version: Mapped[str] = mapped_column(String(32), default="")
    endpoint_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    cluster_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    platform_version: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    present: Mapped[bool] = mapped_column(Boolean, default=True)


class EksClusterHealthRow(Base):
    __tablename__ = "eks_cluster_health"

    cluster_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    control_plane_status: Mapped[str] = mapped_column(String(32), nullable=False)
    kubernetes_api_reachable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    ready_node_count: Mapped[int] = mapped_column(Integer, default=0)
    pod_count: Mapped[int] = mapped_column(Integer, default=0)
    unhealthy_pod_count: Mapped[int] = mapped_column(Integer, default=0)
    crashloop_backoff_count: Mapped[int] = mapped_column(Integer, default=0)
    pending_pod_count: Mapped[int] = mapped_column(Integer, default=0)
    unavailable_deployment_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_job_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")


class AcmCertificateRow(Base):
    __tablename__ = "acm_certificates"
    __table_args__ = (UniqueConstraint("arn", name="uq_acm_certificates_arn"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    arn: Mapped[str] = mapped_column(String(512), nullable=False)
    domain_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_alternative_names: Mapped[str] = mapped_column(Text, default="[]")
    issuer: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    not_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    days_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    in_use_by: Mapped[str] = mapped_column(Text, default="[]")
    renewal_eligibility: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="AWS")
    platform_region: Mapped[str] = mapped_column(String(32), default="EMEA")
    environment: Mapped[str] = mapped_column(String(32), default="DEV")
    account_alias: Mapped[str] = mapped_column(String(128), default="nonprod-emea")
    cloud_region: Mapped[str] = mapped_column(String(64), default="eu-west-1")
    present: Mapped[bool] = mapped_column(Boolean, default=True)


class PlatformJobRow(Base):
    __tablename__ = "platform_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="AWS")
    platform_region: Mapped[str] = mapped_column(String(32), default="EMEA")
    environment: Mapped[str] = mapped_column(String(32), default="DEV")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_class: Mapped[str] = mapped_column(String(64), default="")


class LiveScopeStateRow(Base):
    __tablename__ = "live_scope_state"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_region: Mapped[str] = mapped_column(String(32), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    last_discovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_certificate_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovery_active: Mapped[bool] = mapped_column(Boolean, default=False)
