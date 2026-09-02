"""phase7 certificate monitoring

Revision ID: 0005_phase7_certificates
Revises: 0004_phase6_credentials
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_phase7_certificates"
down_revision = "0004_phase6_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cloud_environments") as batch:
        batch.add_column(sa.Column("last_attempted_scan_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("acm_certificates") as batch:
        batch.add_column(sa.Column("serial_number", sa.String(128), nullable=False, server_default=""))
        batch.add_column(sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("discovery_status", sa.String(32), nullable=False, server_default="ok"))
        batch.add_column(sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("cluster_id", sa.String(128), nullable=False, server_default=""))
        batch.add_column(sa.Column("application_id", sa.String(128), nullable=False, server_default=""))
        batch.add_column(sa.Column("expiry_status", sa.String(32), nullable=False, server_default=""))
        batch.add_column(sa.Column("hostname", sa.String(255), nullable=False, server_default=""))
        batch.add_column(sa.Column("handshake_ok", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("handshake_latency_ms", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_error", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("last_error_class", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "certificate_history_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("certificate_id", sa.String(128), sa.ForeignKey("acm_certificates.id"), nullable=False),
        sa.Column("event", sa.String(48), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "certificate_alerts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("certificate_id", sa.String(128), sa.ForeignKey("acm_certificates.id"), nullable=False),
        sa.Column("kind", sa.String(48), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
        sa.Column("domain", sa.String(255), nullable=False, server_default=""),
        sa.Column("provider", sa.String(32), nullable=False, server_default="AWS"),
        sa.Column("region", sa.String(32), nullable=False, server_default=""),
        sa.Column("account", sa.String(128), nullable=False, server_default=""),
        sa.Column("environment", sa.String(32), nullable=False, server_default=""),
        sa.Column("cluster", sa.String(255), nullable=False, server_default=""),
        sa.Column("application", sa.String(128), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("days_remaining", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(128), nullable=False, server_default=""),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "certificate_validations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("certificate_id", sa.String(128), sa.ForeignKey("acm_certificates.id"), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False, server_default=""),
        sa.Column("handshake_ok", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issuer", sa.String(255), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "certificate_endpoints",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default=""),
        sa.Column("region", sa.String(32), nullable=False, server_default=""),
        sa.Column("environment", sa.String(32), nullable=False, server_default=""),
        sa.Column("account_alias", sa.String(128), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("url", name="uq_certificate_endpoints_url"),
    )
    op.create_table(
        "notification_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("certificate_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False, server_default="log"),
        sa.Column("payload", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "certificate_audit_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("certificate_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default=""),
        sa.Column("platform_region", sa.String(32), nullable=False, server_default=""),
        sa.Column("environment", sa.String(32), nullable=False, server_default=""),
        sa.Column("result", sa.String(32), nullable=False, server_default="succeeded"),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("correlation_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("certificate_audit_events")
    op.drop_table("notification_events")
    op.drop_table("certificate_endpoints")
    op.drop_table("certificate_validations")
    op.drop_table("certificate_alerts")
    op.drop_table("certificate_history_events")
    with op.batch_alter_table("acm_certificates") as batch:
        batch.drop_column("last_attempted_at")
        batch.drop_column("last_error_class")
        batch.drop_column("last_error")
        batch.drop_column("handshake_latency_ms")
        batch.drop_column("handshake_ok")
        batch.drop_column("hostname")
        batch.drop_column("expiry_status")
        batch.drop_column("application_id")
        batch.drop_column("cluster_id")
        batch.drop_column("last_seen_at")
        batch.drop_column("first_seen_at")
        batch.drop_column("discovery_status")
        batch.drop_column("auto_renew")
        batch.drop_column("serial_number")
    with op.batch_alter_table("cloud_environments") as batch:
        batch.drop_column("last_attempted_scan_at")
