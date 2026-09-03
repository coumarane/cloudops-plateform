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
    managed_provider_id: Mapped[str] = mapped_column(String(64), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    auth_strategy: Mapped[str] = mapped_column(String(32), default="")
    ram_role: Mapped[str] = mapped_column(String(512), default="")
    cloud_regions_json: Mapped[str] = mapped_column(Text, default="[]")
    last_error_class: Mapped[str] = mapped_column(String(64), default="")
    identity_account: Mapped[str] = mapped_column(String(64), default="")
    identity_principal: Mapped[str] = mapped_column(String(255), default="")


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
    last_attempted_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    code: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    readiness_status: Mapped[str] = mapped_column(String(32), default="NOT_CONFIGURED")


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
    ignored: Mapped[bool] = mapped_column(Boolean, default=False)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


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
    serial_number: Mapped[str] = mapped_column(String(128), default="")
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    discovery_status: Mapped[str] = mapped_column(String(32), default="ok")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    application_id: Mapped[str] = mapped_column(String(128), default="")
    expiry_status: Mapped[str] = mapped_column(String(32), default="")
    hostname: Mapped[str] = mapped_column(String(255), default="")
    handshake_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    handshake_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_error_class: Mapped[str] = mapped_column(String(64), default="")
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    resources_found: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)


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


class CertificateHistoryRow(Base):
    __tablename__ = "certificate_history_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    certificate_id: Mapped[str] = mapped_column(String(128), ForeignKey("acm_certificates.id"), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CertificateAlertRow(Base):
    __tablename__ = "certificate_alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    certificate_id: Mapped[str] = mapped_column(String(128), ForeignKey("acm_certificates.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", index=True)
    domain: Mapped[str] = mapped_column(String(255), default="")
    provider: Mapped[str] = mapped_column(String(32), default="AWS")
    region: Mapped[str] = mapped_column(String(32), default="")
    account: Mapped[str] = mapped_column(String(128), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    cluster: Mapped[str] = mapped_column(String(255), default="")
    application: Mapped[str] = mapped_column(String(128), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    days_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str] = mapped_column(String(128), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CertificateValidationRow(Base):
    __tablename__ = "certificate_validations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    certificate_id: Mapped[str] = mapped_column(String(128), ForeignKey("acm_certificates.id"), nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String(255), default="")
    handshake_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    issuer: Mapped[str] = mapped_column(String(255), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CertificateEndpointRow(Base):
    __tablename__ = "certificate_endpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    region: Mapped[str] = mapped_column(String(32), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    account_alias: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationEventRow(Base):
    __tablename__ = "notification_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    certificate_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="log")
    payload: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CertificateAuditRow(Base):
    __tablename__ = "certificate_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    certificate_id: Mapped[str] = mapped_column(String(128), default="")
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="")
    platform_region: Mapped[str] = mapped_column(String(32), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    result: Mapped[str] = mapped_column(String(32), default="succeeded")
    detail: Mapped[str] = mapped_column(Text, default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GithubIntegrationRow(Base):
    __tablename__ = "github_integrations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_id: Mapped[str] = mapped_column(String(64), nullable=False)
    installation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    organization: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    api_url: Mapped[str] = mapped_column(String(255), nullable=False, default="https://api.github.com")
    private_key_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    webhook_secret_ref: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_error_class: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GithubOrganizationRow(Base):
    __tablename__ = "github_organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    integration_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_integrations.id"), nullable=False)
    github_id: Mapped[str] = mapped_column(String(64), nullable=False)
    login: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    html_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="ok")
    last_synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GithubRepositoryRow(Base):
    __tablename__ = "github_repositories"
    __table_args__ = (UniqueConstraint("github_id", name="uq_github_repositories_github_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_organizations.id"), nullable=False)
    github_id: Mapped[str] = mapped_column(String(64), nullable=False)
    organization: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    default_branch: Mapped[str] = mapped_column(String(128), default="main")
    visibility: Mapped[str] = mapped_column(String(32), default="private")
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    html_url: Mapped[str] = mapped_column(String(512), default="")
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GithubApplicationRepositoryRow(Base):
    __tablename__ = "github_application_repositories"
    __table_args__ = (UniqueConstraint("repository_id", "application_id", name="uq_github_app_repo"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repository_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_repositories.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GithubEnvironmentMappingRow(Base):
    __tablename__ = "github_environment_mapping"
    __table_args__ = (
        UniqueConstraint("github_repository_id", "github_environment", name="uq_github_env_mapping"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    github_repository_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_repositories.id"), nullable=False)
    github_environment: Mapped[str] = mapped_column(String(128), nullable=False)
    cloudops_environment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GithubWorkflowRow(Base):
    __tablename__ = "github_workflows"
    __table_args__ = (UniqueConstraint("github_id", name="uq_github_workflows_github_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repository_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_repositories.id"), nullable=False)
    github_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(512), default="")
    state: Mapped[str] = mapped_column(String(32), default="active")
    html_url: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GithubWorkflowRunRow(Base):
    __tablename__ = "github_workflow_runs"
    __table_args__ = (UniqueConstraint("github_id", name="uq_github_workflow_runs_github_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_workflows.id"), nullable=False)
    repository_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_repositories.id"), nullable=False)
    github_id: Mapped[str] = mapped_column(String(64), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), default="")
    commit_sha: Mapped[str] = mapped_column(String(64), default="")
    event: Mapped[str] = mapped_column(String(64), default="")
    actor: Mapped[str] = mapped_column(String(128), default="")
    github_status: Mapped[str] = mapped_column(String(32), default="")
    github_conclusion: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_attempt: Mapped[int] = mapped_column(Integer, default=1)
    html_url: Mapped[str] = mapped_column(String(512), default="")
    github_environment: Mapped[str] = mapped_column(String(128), default="")
    cloudops_environment_id: Mapped[str] = mapped_column(String(128), default="")
    application_id: Mapped[str] = mapped_column(String(128), default="")
    deployment_id: Mapped[str] = mapped_column(String(128), default="")
    cluster_id: Mapped[str] = mapped_column(String(128), default="")


class GithubWorkflowJobRow(Base):
    __tablename__ = "github_workflow_jobs"
    __table_args__ = (UniqueConstraint("github_id", name="uq_github_workflow_jobs_github_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_workflow_runs.id"), nullable=False)
    github_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_status: Mapped[str] = mapped_column(String(32), default="")
    github_conclusion: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runner_name: Mapped[str] = mapped_column(String(128), default="")
    runner_type: Mapped[str] = mapped_column(String(128), default="")
    html_url: Mapped[str] = mapped_column(String(512), default="")


class GithubVariableRow(Base):
    __tablename__ = "github_variables"
    __table_args__ = (
        UniqueConstraint("repository_id", "name", "scope", "github_environment", name="uq_github_variables"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repository_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_repositories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="repository")
    github_environment: Mapped[str] = mapped_column(String(128), default="")
    organization: Mapped[str] = mapped_column(String(128), default="")
    value_masked: Mapped[str] = mapped_column(String(64), default="••••••••••••")
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cloudops_environment_id: Mapped[str] = mapped_column(String(128), default="")


class GithubSecretRow(Base):
    __tablename__ = "github_secrets"
    __table_args__ = (
        UniqueConstraint("repository_id", "name", "scope", "github_environment", name="uq_github_secrets"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repository_id: Mapped[str] = mapped_column(String(64), ForeignKey("github_repositories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="repository")
    github_environment: Mapped[str] = mapped_column(String(128), default="")
    organization: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cloudops_environment_id: Mapped[str] = mapped_column(String(128), default="")


class GithubWebhookDeliveryRow(Base):
    __tablename__ = "github_webhook_deliveries"
    __table_args__ = (UniqueConstraint("delivery_id", name="uq_github_webhook_delivery"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    delivery_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), default="")
    payload_digest: Mapped[str] = mapped_column(String(64), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GithubAuditRow(Base):
    __tablename__ = "github_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    object_name: Mapped[str] = mapped_column(String(255), default="")
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    result: Mapped[str] = mapped_column(String(32), default="succeeded")
    detail: Mapped[str] = mapped_column(Text, default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GithubAlertRow(Base):
    __tablename__ = "github_alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), default="")
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    workflow_id: Mapped[str] = mapped_column(String(64), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    title: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelineProviderRow(Base):
    __tablename__ = "pipeline_providers"
    __table_args__ = (UniqueConstraint("key", name="uq_pipeline_providers_key"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    organization: Mapped[str] = mapped_column(String(128), default="")
    project: Mapped[str] = mapped_column(String(128), default="")
    base_url: Mapped[str] = mapped_column(String(255), default="")
    auth_ref: Mapped[str] = mapped_column(String(512), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    last_attempted_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    last_error_class: Mapped[str] = mapped_column(String(64), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PipelineRow(Base):
    __tablename__ = "pipelines"
    __table_args__ = (UniqueConstraint("provider_id", "external_id", name="uq_pipelines_provider_external"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(64), ForeignKey("pipeline_providers.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    application_id: Mapped[str] = mapped_column(String(128), default="")
    default_branch: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    html_url: Mapped[str] = mapped_column(String(512), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelineRunRow(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (UniqueConstraint("pipeline_id", "external_run_id", name="uq_pipeline_runs_external"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(64), ForeignKey("pipelines.id"), nullable=False)
    external_run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), default="")
    commit_sha: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[str] = mapped_column(String(128), default="")
    trigger: Mapped[str] = mapped_column(String(64), default="")
    actor: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    provider_status: Mapped[str] = mapped_column(String(64), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_url: Mapped[str] = mapped_column(String(512), default="")
    environment_id: Mapped[str] = mapped_column(String(128), default="")
    deployment_id: Mapped[str] = mapped_column(String(128), default="")
    application_id: Mapped[str] = mapped_column(String(128), default="")
    repository_id: Mapped[str] = mapped_column(String(64), default="")
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PipelineStageRow(Base):
    __tablename__ = "pipeline_stages"
    __table_args__ = (UniqueConstraint("run_id", "external_id", name="uq_pipeline_stages_external"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("pipeline_runs.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    provider_status: Mapped[str] = mapped_column(String(64), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    html_url: Mapped[str] = mapped_column(String(512), default="")


class PipelineJobRow(Base):
    __tablename__ = "pipeline_jobs"
    __table_args__ = (UniqueConstraint("run_id", "external_id", name="uq_pipeline_jobs_external"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("pipeline_runs.id"), nullable=False)
    stage_id: Mapped[str] = mapped_column(String(64), default="")
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    provider_status: Mapped[str] = mapped_column(String(64), default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    html_url: Mapped[str] = mapped_column(String(512), default="")


class PipelineEnvironmentMappingRow(Base):
    __tablename__ = "pipeline_environment_mapping"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_id",
            "environment_id",
            "branch_pattern",
            "stage_name",
            name="uq_pipeline_env_mapping",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(64), ForeignKey("pipelines.id"), nullable=False)
    environment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_pattern: Mapped[str] = mapped_column(String(128), default="*")
    stage_name: Mapped[str] = mapped_column(String(128), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PipelineApplicationMappingRow(Base):
    __tablename__ = "pipeline_application_mapping"
    __table_args__ = (UniqueConstraint("pipeline_id", "application_id", name="uq_pipeline_app_mapping"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(64), ForeignKey("pipelines.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PipelineWebhookDeliveryRow(Base):
    __tablename__ = "pipeline_webhook_deliveries"
    __table_args__ = (UniqueConstraint("delivery_id", name="uq_pipeline_webhook_delivery"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    delivery_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(32), nullable=False)
    event: Mapped[str] = mapped_column(String(64), default="")
    payload_digest: Mapped[str] = mapped_column(String(64), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PipelineAuditRow(Base):
    __tablename__ = "pipeline_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    object_name: Mapped[str] = mapped_column(String(255), default="")
    pipeline_id: Mapped[str] = mapped_column(String(64), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    result: Mapped[str] = mapped_column(String(32), default="succeeded")
    detail: Mapped[str] = mapped_column(Text, default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PipelineAlertRow(Base):
    __tablename__ = "pipeline_alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), default="")
    pipeline_id: Mapped[str] = mapped_column(String(64), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    title: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HealthCheckDefinitionRow(Base):
    __tablename__ = "health_check_definition"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    check_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=120)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=5)
    retries: Mapped[int] = mapped_column(Integer, default=1)
    severity: Mapped[str] = mapped_column(String(16), default="HIGH")
    environment_id: Mapped[str] = mapped_column(String(128), default="")
    application_id: Mapped[str] = mapped_column(String(128), default="")
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    url: Mapped[str] = mapped_column(String(512), default="")
    method: Mapped[str] = mapped_column(String(16), default="GET")
    expected_status: Mapped[str] = mapped_column(String(64), default="200-299")
    expected_pattern: Mapped[str] = mapped_column(String(255), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_category: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HealthCheckResultRow(Base):
    __tablename__ = "health_check_result"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    definition_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    application_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    environment_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(String(512), default="")
    error_category: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ResourceHealthRow(Base):
    __tablename__ = "resource_health"
    __table_args__ = (
        UniqueConstraint("cluster_id", "resource_type", "namespace", "resource_name", name="uq_resource_health_ref"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_name: Mapped[str] = mapped_column(String(255), nullable=False)
    namespace: Mapped[str] = mapped_column(String(128), default="")
    cluster_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    environment_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    application_id: Mapped[str] = mapped_column(String(128), default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    region: Mapped[str] = mapped_column(String(32), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(String(512), default="")
    check_type: Mapped[str] = mapped_column(String(64), default="")
    error_category: Mapped[str] = mapped_column(String(64), default="")
    desired: Mapped[int] = mapped_column(Integer, default=0)
    ready: Mapped[int] = mapped_column(Integer, default=0)
    available: Mapped[int] = mapped_column(Integer, default=0)
    unavailable: Mapped[int] = mapped_column(Integer, default=0)
    restart_count: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(128), default="")
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplicationHealthRow(Base):
    __tablename__ = "application_health"
    __table_args__ = (UniqueConstraint("application_id", "environment_id", name="uq_application_health_scope"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    application_name: Mapped[str] = mapped_column(String(255), default="")
    environment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    region: Mapped[str] = mapped_column(String(32), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(String(512), default="")
    likely_cause: Mapped[str] = mapped_column(String(255), default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    correlation_json: Mapped[str] = mapped_column(Text, default="{}")
    consecutive_unhealthy: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_healthy: Mapped[int] = mapped_column(Integer, default=0)
    desired_replicas: Mapped[int] = mapped_column(Integer, default=0)
    available_replicas: Mapped[int] = mapped_column(Integer, default=0)
    crashloop: Mapped[int] = mapped_column(Integer, default=0)
    failed_pods: Mapped[int] = mapped_column(Integer, default=0)
    restart_count: Mapped[int] = mapped_column(Integer, default=0)
    http_status: Mapped[str] = mapped_column(String(16), default="")
    ingress_status: Mapped[str] = mapped_column(String(16), default="")
    certificate_status: Mapped[str] = mapped_column(String(16), default="")
    pipeline_status: Mapped[str] = mapped_column(String(32), default="")
    deployment_status: Mapped[str] = mapped_column(String(32), default="")
    cluster_status: Mapped[str] = mapped_column(String(16), default="")
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_category: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HealthIncidentRow(Base):
    __tablename__ = "health_incident"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    environment_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    region: Mapped[str] = mapped_column(String(32), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="HIGH")
    root_symptom: Mapped[str] = mapped_column(String(255), default="")
    affected_resources_json: Mapped[str] = mapped_column(Text, default="[]")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str] = mapped_column(String(128), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplicationResourceMappingRow(Base):
    __tablename__ = "application_resource_mapping"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    environment_id: Mapped[str] = mapped_column(String(128), default="")
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    namespace: Mapped[str] = mapped_column(String(128), default="")
    resource_type: Mapped[str] = mapped_column(String(32), default="")
    resource_name: Mapped[str] = mapped_column(String(255), default="")
    label_selector: Mapped[str] = mapped_column(String(512), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApplicationDependencyRow(Base):
    __tablename__ = "application_dependency"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_application_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    dependency_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_application_id: Mapped[str] = mapped_column(String(128), default="")
    external_name: Mapped[str] = mapped_column(String(255), default="")
    health_check_definition_id: Mapped[str] = mapped_column(String(64), default="")
    credential_ref: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HealthAlertRow(Base):
    __tablename__ = "health_alerts"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_health_alert_fingerprint"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    application_id: Mapped[str] = mapped_column(String(128), default="")
    environment_id: Mapped[str] = mapped_column(String(128), default="")
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    severity: Mapped[str] = mapped_column(String(16), default="HIGH")
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    title: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HealthTimelineEventRow(Base):
    __tablename__ = "health_timeline_event"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    environment_id: Mapped[str] = mapped_column(String(128), default="")
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(String(512), default="")
    href: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class HealthAuditRow(Base):
    __tablename__ = "health_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    object_name: Mapped[str] = mapped_column(String(255), default="")
    result: Mapped[str] = mapped_column(String(32), default="succeeded")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HealthScanLockRow(Base):
    __tablename__ = "health_scan_lock"

    environment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), default="")
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AlertRow(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    region: Mapped[str] = mapped_column(String(32), default="")
    account_id: Mapped[str] = mapped_column(String(128), default="")
    environment_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    environment: Mapped[str] = mapped_column(String(32), default="")
    application_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(String(512), default="")
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str] = mapped_column(String(128), default="")
    acknowledged_comment: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_reason: Mapped[str] = mapped_column(String(255), default="")
    correlation_id: Mapped[str] = mapped_column(String(64), default="")
    extra_json: Mapped[str] = mapped_column(Text, default="{}")
    rule_id: Mapped[str] = mapped_column(String(64), default="")
    policy_id: Mapped[str] = mapped_column(String(64), default="")


class AlertEventRow(Base):
    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(String(512), default="")
    actor: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class AlertRuleRow(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    provider_filter: Mapped[str] = mapped_column(String(32), default="")
    region_filter: Mapped[str] = mapped_column(String(32), default="")
    environment_filter: Mapped[str] = mapped_column(String(32), default="")
    application_filter: Mapped[str] = mapped_column(String(128), default="")
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    minimum_occurrences: Mapped[int] = mapped_column(Integer, default=1)
    evaluation_window_seconds: Mapped[int] = mapped_column(Integer, default=0)
    notification_policy_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationDestinationRow(Base):
    __tablename__ = "notification_destinations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration_reference: Mapped[str] = mapped_column(String(256), default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationPolicyRow(Base):
    __tablename__ = "notification_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    initial_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    repeat_after_seconds: Mapped[int] = mapped_column(Integer, default=0)
    escalate_after_seconds: Mapped[int] = mapped_column(Integer, default=0)
    recovery_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationPolicyStepRow(Base):
    __tablename__ = "notification_policy_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    destination_id: Mapped[str] = mapped_column(String(64), default="")
    step_type: Mapped[str] = mapped_column(String(24), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AlertRoutingRuleRow(Base):
    __tablename__ = "alert_routing_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    provider_filter: Mapped[str] = mapped_column(String(32), default="")
    region_filter: Mapped[str] = mapped_column(String(32), default="")
    account_filter: Mapped[str] = mapped_column(String(128), default="")
    environment_filter: Mapped[str] = mapped_column(String(32), default="")
    application_filter: Mapped[str] = mapped_column(String(128), default="")
    severity_filter: Mapped[str] = mapped_column(String(16), default="")
    alert_type_filter: Mapped[str] = mapped_column(String(64), default="")
    destination_id: Mapped[str] = mapped_column(String(64), default="")
    policy_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationDeliveryRow(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    destination_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_category: Mapped[str] = mapped_column(String(32), default="")
    external_message_id: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[str] = mapped_column(String(512), default="")


class AlertSuppressionRow(Base):
    __tablename__ = "alert_suppressions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(128), default="")
    alert_type: Mapped[str] = mapped_column(String(64), default="")
    reason: Mapped[str] = mapped_column(String(255), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class MaintenanceWindowRow(Base):
    __tablename__ = "maintenance_windows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    region: Mapped[str] = mapped_column(String(32), default="")
    environment: Mapped[str] = mapped_column(String(32), default="")
    application: Mapped[str] = mapped_column(String(128), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="")
    change_ticket: Mapped[str] = mapped_column(String(64), default="")
    created_by: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ManagedProviderRow(Base):
    __tablename__ = "managed_providers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auth_strategy: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(32), default="NOT_CONFIGURED")
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="")
    error_category: Mapped[str] = mapped_column(String(64), default="")
    identity_account: Mapped[str] = mapped_column(String(64), default="")
    identity_principal: Mapped[str] = mapped_column(String(255), default="")
    extra_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ManagedApplicationRow(Base):
    __tablename__ = "managed_applications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    owner_team: Mapped[str] = mapped_column(String(128), default="")
    repository_id: Mapped[str] = mapped_column(String(128), default="")
    pipeline_id: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApplicationEnvironmentBindingRow(Base):
    __tablename__ = "application_environment_bindings"
    __table_args__ = (UniqueConstraint("application_id", "environment_id", name="uq_app_env_binding"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(64), ForeignKey("managed_applications.id"), nullable=False)
    environment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cluster_id: Mapped[str] = mapped_column(String(128), default="")
    namespace: Mapped[str] = mapped_column(String(255), default="")
    workload: Mapped[str] = mapped_column(String(255), default="")
    health_endpoint: Mapped[str] = mapped_column(String(512), default="")


class PlatformSettingRow(Base):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), default="")


class PlatformAuditRow(Base):
    __tablename__ = "platform_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    object_name: Mapped[str] = mapped_column(String(255), default="")
    result: Mapped[str] = mapped_column(String(32), default="succeeded")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AlertAuditRow(Base):
    __tablename__ = "alert_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    object_name: Mapped[str] = mapped_column(String(255), default="")
    result: Mapped[str] = mapped_column(String(32), default="succeeded")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
