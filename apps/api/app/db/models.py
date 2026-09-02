from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CloudProviderRow(Base):
    __tablename__ = "cloud_providers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class PlatformRegionRow(Base):
    __tablename__ = "platform_regions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), ForeignKey("cloud_providers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    cloud_region: Mapped[str] = mapped_column(String(64), nullable=False)


class CloudAccountRow(Base):
    __tablename__ = "cloud_accounts"
    __table_args__ = (UniqueConstraint("alias", name="uq_cloud_accounts_alias"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_region: Mapped[str] = mapped_column(String(32), nullable=False)
    cloud_region: Mapped[str] = mapped_column(String(64), nullable=False)
    alias: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(32), default="")
    role_arn: Mapped[str] = mapped_column(String(512), default="")
    external_id: Mapped[str] = mapped_column(String(256), default="")
    account_class: Mapped[str] = mapped_column(String(32), nullable=False)
    readonly: Mapped[bool] = mapped_column(Boolean, default=False)
    session_name: Mapped[str] = mapped_column(String(128), default="")
    cluster_environment_tag: Mapped[str] = mapped_column(String(64), default="Environment")
    credential_ref: Mapped[str] = mapped_column(String(256), default="")
    credential_fingerprint: Mapped[str] = mapped_column(String(64), default="")
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="")


class CloudEnvironmentRow(Base):
    __tablename__ = "cloud_environments"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(128), ForeignKey("cloud_accounts.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_region: Mapped[str] = mapped_column(String(32), nullable=False)
    cloud_region: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    account_alias: Mapped[str] = mapped_column(String(128), nullable=False)
    readonly: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    discovery_active: Mapped[bool] = mapped_column(Boolean, default=False)
    last_discovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_certificate_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_error_class: Mapped[str] = mapped_column(String(64), default="")
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    environment_id: Mapped[str] = mapped_column(String(128), default="")
    cluster_type: Mapped[str] = mapped_column(String(64), default="")
    extra_json: Mapped[str] = mapped_column(Text, default="{}")


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
    stateful_set_unhealthy_count: Mapped[int] = mapped_column(Integer, default=0)
    ingress_unhealthy_count: Mapped[int] = mapped_column(Integer, default=0)
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
    cluster_name: Mapped[str] = mapped_column(String(255), default="")
    namespace: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(32), default="")


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
    target_id: Mapped[str] = mapped_column(String(128), default="")


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


class CredentialRow(Base):
    __tablename__ = "credentials"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "platform_region",
            "account_alias",
            "environment",
            "name",
            name="uq_credentials_scope_name",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_region: Mapped[str] = mapped_column(String(32), nullable=False)
    account_alias: Mapped[str] = mapped_column(String(128), nullable=False)
    account_id: Mapped[str] = mapped_column(String(32), default="")
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    environment_id: Mapped[str] = mapped_column(String(128), default="")
    credential_type: Mapped[str] = mapped_column(String(64), nullable=False)
    secret_backend: Mapped[str] = mapped_column(String(32), nullable=False)
    secret_reference: Mapped[str] = mapped_column(String(512), default="")
    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="HEALTHY")
    rotation_policy_days: Mapped[int] = mapped_column(Integer, default=90)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotation_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), default="")
    role_arn: Mapped[str] = mapped_column(String(512), default="")
    external_id_ref: Mapped[str] = mapped_column(String(256), default="")
    cloud_region: Mapped[str] = mapped_column(String(64), default="")
    extra_json: Mapped[str] = mapped_column(Text, default="{}")


class CredentialVersionRow(Base):
    __tablename__ = "credential_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    credential_id: Mapped[str] = mapped_column(String(64), ForeignKey("credentials.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    secret_reference: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="")


class CredentialValidationRow(Base):
    __tablename__ = "credential_validations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    credential_id: Mapped[str] = mapped_column(String(64), ForeignKey("credentials.id"), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_category: Mapped[str] = mapped_column(String(64), default="")
    provider_account: Mapped[str] = mapped_column(String(64), default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CredentialRotationEventRow(Base):
    __tablename__ = "credential_rotation_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    credential_id: Mapped[str] = mapped_column(String(64), ForeignKey("credentials.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CredentialAuditRow(Base):
    __tablename__ = "credential_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_id: Mapped[str] = mapped_column(String(64), default="")
    credential_name: Mapped[str] = mapped_column(String(255), default="")
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="")
    platform_region: Mapped[str] = mapped_column(String(32), default="")
    account_alias: Mapped[str] = mapped_column(String(128), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    change_ticket: Mapped[str] = mapped_column(String(128), default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
