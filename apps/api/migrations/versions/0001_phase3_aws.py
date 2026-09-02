"""phase3 aws inventory

Revision ID: 0001_phase3_aws
Revises:
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_phase3_aws"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eks_clusters",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("arn", sa.String(512), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("cloud_region", sa.String(64), nullable=False),
        sa.Column("aws_account_id", sa.String(32), nullable=False),
        sa.Column("account_alias", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="AWS"),
        sa.Column("platform_region", sa.String(32), nullable=False, server_default="EMEA"),
        sa.Column("environment", sa.String(32), nullable=False, server_default="DEV"),
        sa.Column("kubernetes_version", sa.String(32), nullable=False, server_default=""),
        sa.Column("endpoint_status", sa.String(32), nullable=False, server_default="UNKNOWN"),
        sa.Column("cluster_status", sa.String(32), nullable=False, server_default="UNKNOWN"),
        sa.Column("platform_version", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("arn", name="uq_eks_clusters_arn"),
    )
    op.create_table(
        "eks_cluster_health",
        sa.Column("cluster_id", sa.String(128), primary_key=True),
        sa.Column("control_plane_status", sa.String(32), nullable=False),
        sa.Column("kubernetes_api_reachable", sa.Boolean(), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ready_node_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pod_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unhealthy_pod_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("crashloop_backoff_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_pod_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unavailable_deployment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_checked", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "acm_certificates",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("arn", sa.String(512), nullable=False),
        sa.Column("domain_name", sa.String(255), nullable=False),
        sa.Column("subject_alternative_names", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("issuer", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(64), nullable=False, server_default="UNKNOWN"),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=True),
        sa.Column("not_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("days_remaining", sa.Integer(), nullable=True),
        sa.Column("in_use_by", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("renewal_eligibility", sa.String(64), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_checked", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="AWS"),
        sa.Column("platform_region", sa.String(32), nullable=False, server_default="EMEA"),
        sa.Column("environment", sa.String(32), nullable=False, server_default="DEV"),
        sa.Column("account_alias", sa.String(128), nullable=False, server_default="nonprod-emea"),
        sa.Column("cloud_region", sa.String(64), nullable=False, server_default="eu-west-1"),
        sa.Column("present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("arn", name="uq_acm_certificates_arn"),
    )
    op.create_table(
        "platform_jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="AWS"),
        sa.Column("platform_region", sa.String(32), nullable=False, server_default="EMEA"),
        sa.Column("environment", sa.String(32), nullable=False, server_default="DEV"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_class", sa.String(64), nullable=False, server_default=""),
    )
    op.create_table(
        "live_scope_state",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("platform_region", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("last_discovery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_certificate_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovery_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("live_scope_state")
    op.drop_table("platform_jobs")
    op.drop_table("acm_certificates")
    op.drop_table("eks_cluster_health")
    op.drop_table("eks_clusters")
