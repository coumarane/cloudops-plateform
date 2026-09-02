"""phase7 certificate monitoring

Revision ID: 0005_phase7_certificates
Revises: 0004_phase6_credentials
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_phase7_certificates"
down_revision = "0004_phase6_credentials"
branch_labels = None
depends_on = None


def _inspector():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _columns(table: str) -> set[str]:
    if not _has_table(table):
        return set()
    return {column["name"] for column in _inspector().get_columns(table)}


def _add_columns(table: str, columns: list[sa.Column]) -> None:
    existing = _columns(table)
    missing = [column for column in columns if column.name not in existing]
    if not missing:
        return
    with op.batch_alter_table(table) as batch:
        for column in missing:
            batch.add_column(column)


def upgrade() -> None:
    if _has_table("_alembic_tmp_acm_certificates"):
        op.drop_table("_alembic_tmp_acm_certificates")

    _add_columns(
        "cloud_environments",
        [sa.Column("last_attempted_scan_at", sa.DateTime(timezone=True), nullable=True)],
    )
    _add_columns(
        "acm_certificates",
        [
            sa.Column("serial_number", sa.String(128), nullable=False, server_default=""),
            sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("discovery_status", sa.String(32), nullable=False, server_default="ok"),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cluster_id", sa.String(128), nullable=False, server_default=""),
            sa.Column("application_id", sa.String(128), nullable=False, server_default=""),
            sa.Column("expiry_status", sa.String(32), nullable=False, server_default=""),
            sa.Column("hostname", sa.String(255), nullable=False, server_default=""),
            sa.Column("handshake_ok", sa.Boolean(), nullable=True),
            sa.Column("handshake_latency_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
            sa.Column("last_error_class", sa.String(64), nullable=False, server_default=""),
            sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        ],
    )

    if not _has_table("certificate_history_events"):
        op.create_table(
            "certificate_history_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("certificate_id", sa.String(128), sa.ForeignKey("acm_certificates.id"), nullable=False),
            sa.Column("event", sa.String(48), nullable=False),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("certificate_alerts"):
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
    if not _has_table("certificate_validations"):
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
    if not _has_table("certificate_endpoints"):
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
    if not _has_table("notification_events"):
        op.create_table(
            "notification_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("certificate_id", sa.String(128), nullable=False, server_default=""),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("channel", sa.String(32), nullable=False, server_default="log"),
            sa.Column("payload", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("certificate_audit_events"):
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
    if _has_table("certificate_audit_events"):
        op.drop_table("certificate_audit_events")
    if _has_table("notification_events"):
        op.drop_table("notification_events")
    if _has_table("certificate_endpoints"):
        op.drop_table("certificate_endpoints")
    if _has_table("certificate_validations"):
        op.drop_table("certificate_validations")
    if _has_table("certificate_alerts"):
        op.drop_table("certificate_alerts")
    if _has_table("certificate_history_events"):
        op.drop_table("certificate_history_events")
    drop_acm = [
        "last_attempted_at",
        "last_error_class",
        "last_error",
        "handshake_latency_ms",
        "handshake_ok",
        "hostname",
        "expiry_status",
        "application_id",
        "cluster_id",
        "last_seen_at",
        "first_seen_at",
        "discovery_status",
        "auto_renew",
        "serial_number",
    ]
    existing_acm = _columns("acm_certificates")
    missing_drops = [name for name in drop_acm if name in existing_acm]
    if missing_drops:
        with op.batch_alter_table("acm_certificates") as batch:
            for name in missing_drops:
                batch.drop_column(name)
    if "last_attempted_scan_at" in _columns("cloud_environments"):
        with op.batch_alter_table("cloud_environments") as batch:
            batch.drop_column("last_attempted_scan_at")
