"""phase11 centralized alerting and notifications

Revision ID: 0009_phase11_alerting
Revises: 0008_phase10_health
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0009_phase11_alerting"
down_revision = "0008_phase10_health"
branch_labels = None
depends_on = None


def _inspector():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def upgrade() -> None:
    if not _has_table("alerts"):
        op.create_table(
            "alerts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("alert_type", sa.String(64), nullable=False),
            sa.Column("source_type", sa.String(32), nullable=False),
            sa.Column("source_id", sa.String(128), nullable=False),
            sa.Column("provider", sa.String(32), server_default=""),
            sa.Column("region", sa.String(32), server_default=""),
            sa.Column("account_id", sa.String(128), server_default=""),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("severity", sa.String(16), nullable=False),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("title", sa.String(255), server_default=""),
            sa.Column("summary", sa.String(512), server_default=""),
            sa.Column("fingerprint", sa.String(64), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("occurrence_count", sa.Integer(), server_default="1"),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("acknowledged_by", sa.String(128), server_default=""),
            sa.Column("acknowledged_comment", sa.Text(), server_default=""),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution_reason", sa.String(255), server_default=""),
            sa.Column("correlation_id", sa.String(64), server_default=""),
            sa.Column("extra_json", sa.Text(), server_default="{}"),
            sa.Column("rule_id", sa.String(64), server_default=""),
            sa.Column("policy_id", sa.String(64), server_default=""),
        )
        op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
        op.create_index("ix_alerts_source_id", "alerts", ["source_id"])
        op.create_index("ix_alerts_environment_id", "alerts", ["environment_id"])
        op.create_index("ix_alerts_application_id", "alerts", ["application_id"])
        op.create_index("ix_alerts_severity", "alerts", ["severity"])
        op.create_index("ix_alerts_status", "alerts", ["status"])
        op.create_index("ix_alerts_fingerprint", "alerts", ["fingerprint"])
    if not _has_table("alert_events"):
        op.create_table(
            "alert_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("alert_id", sa.String(64), nullable=False),
            sa.Column("event_type", sa.String(48), nullable=False),
            sa.Column("title", sa.String(255), server_default=""),
            sa.Column("detail", sa.String(512), server_default=""),
            sa.Column("actor", sa.String(128), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_alert_events_alert_id", "alert_events", ["alert_id"])
        op.create_index("ix_alert_events_created_at", "alert_events", ["created_at"])
    if not _has_table("alert_rules"):
        op.create_table(
            "alert_rules",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("alert_type", sa.String(64), server_default=""),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("provider_filter", sa.String(32), server_default=""),
            sa.Column("region_filter", sa.String(32), server_default=""),
            sa.Column("environment_filter", sa.String(32), server_default=""),
            sa.Column("application_filter", sa.String(128), server_default=""),
            sa.Column("severity", sa.String(16), server_default="MEDIUM"),
            sa.Column("minimum_occurrences", sa.Integer(), server_default="1"),
            sa.Column("evaluation_window_seconds", sa.Integer(), server_default="0"),
            sa.Column("notification_policy_id", sa.String(64), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("notification_destinations"):
        op.create_table(
            "notification_destinations",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("provider_type", sa.String(32), nullable=False),
            sa.Column("configuration_reference", sa.String(256), server_default=""),
            sa.Column("config_json", sa.Text(), server_default="{}"),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("description", sa.String(255), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("notification_policies"):
        op.create_table(
            "notification_policies",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("initial_enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("repeat_after_seconds", sa.Integer(), server_default="0"),
            sa.Column("escalate_after_seconds", sa.Integer(), server_default="0"),
            sa.Column("recovery_enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("notification_policy_steps"):
        op.create_table(
            "notification_policy_steps",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("policy_id", sa.String(64), nullable=False),
            sa.Column("delay_seconds", sa.Integer(), server_default="0"),
            sa.Column("destination_id", sa.String(64), server_default=""),
            sa.Column("step_type", sa.String(24), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
        )
        op.create_index("ix_notification_policy_steps_policy_id", "notification_policy_steps", ["policy_id"])
    if not _has_table("alert_routing_rules"):
        op.create_table(
            "alert_routing_rules",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("provider_filter", sa.String(32), server_default=""),
            sa.Column("region_filter", sa.String(32), server_default=""),
            sa.Column("account_filter", sa.String(128), server_default=""),
            sa.Column("environment_filter", sa.String(32), server_default=""),
            sa.Column("application_filter", sa.String(128), server_default=""),
            sa.Column("severity_filter", sa.String(16), server_default=""),
            sa.Column("alert_type_filter", sa.String(64), server_default=""),
            sa.Column("destination_id", sa.String(64), server_default=""),
            sa.Column("policy_id", sa.String(64), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("notification_deliveries"):
        op.create_table(
            "notification_deliveries",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("alert_id", sa.String(64), nullable=False),
            sa.Column("destination_id", sa.String(64), nullable=False),
            sa.Column("notification_type", sa.String(32), nullable=False),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("attempt", sa.Integer(), server_default="0"),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_category", sa.String(32), server_default=""),
            sa.Column("external_message_id", sa.String(128), server_default=""),
            sa.Column("detail", sa.String(512), server_default=""),
        )
        op.create_index("ix_notification_deliveries_alert_id", "notification_deliveries", ["alert_id"])
        op.create_index("ix_notification_deliveries_destination_id", "notification_deliveries", ["destination_id"])
        op.create_index("ix_notification_deliveries_status", "notification_deliveries", ["status"])
    if not _has_table("alert_suppressions"):
        op.create_table(
            "alert_suppressions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("scope_type", sa.String(32), nullable=False),
            sa.Column("reason", sa.String(255), server_default=""),
            sa.Column("scope_id", sa.String(128), server_default=""),
            sa.Column("alert_type", sa.String(64), server_default=""),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by", sa.String(128), server_default=""),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
        )
    if not _has_table("maintenance_windows"):
        op.create_table(
            "maintenance_windows",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("scope", sa.String(64), server_default=""),
            sa.Column("provider", sa.String(32), server_default=""),
            sa.Column("region", sa.String(32), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("application", sa.String(128), server_default=""),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reason", sa.String(255), server_default=""),
            sa.Column("change_ticket", sa.String(64), server_default=""),
            sa.Column("created_by", sa.String(128), server_default=""),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
        )
    if not _has_table("alert_audit_events"):
        op.create_table(
            "alert_audit_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("object_name", sa.String(255), server_default=""),
            sa.Column("result", sa.String(32), server_default="succeeded"),
            sa.Column("detail", sa.Text(), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_alert_audit_events_action", "alert_audit_events", ["action"])


def downgrade() -> None:
    for table in (
        "alert_audit_events",
        "maintenance_windows",
        "alert_suppressions",
        "notification_deliveries",
        "alert_routing_rules",
        "notification_policy_steps",
        "notification_policies",
        "notification_destinations",
        "alert_rules",
        "alert_events",
        "alerts",
    ):
        if _has_table(table):
            op.drop_table(table)
