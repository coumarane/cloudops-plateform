"""phase10 unified application and kubernetes health

Revision ID: 0008_phase10_health
Revises: 0007_phase9_pipelines
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008_phase10_health"
down_revision = "0007_phase9_pipelines"
branch_labels = None
depends_on = None


def _inspector():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def upgrade() -> None:
    if not _has_table("health_check_definition"):
        op.create_table(
            "health_check_definition",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("check_type", sa.String(64), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("interval_seconds", sa.Integer(), server_default="120"),
            sa.Column("timeout_seconds", sa.Integer(), server_default="5"),
            sa.Column("retries", sa.Integer(), server_default="1"),
            sa.Column("severity", sa.String(16), server_default="HIGH"),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("url", sa.String(512), server_default=""),
            sa.Column("method", sa.String(16), server_default="GET"),
            sa.Column("expected_status", sa.String(64), server_default="200-299"),
            sa.Column("expected_pattern", sa.String(255), server_default=""),
            sa.Column("metadata_json", sa.Text(), server_default="{}"),
            sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_successful_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error_category", sa.String(64), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("health_check_result"):
        op.create_table(
            "health_check_result",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("definition_id", sa.String(64), server_default=""),
            sa.Column("resource_id", sa.String(64), server_default=""),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("check_type", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("latency_ms", sa.Integer(), server_default="0"),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("summary", sa.String(512), server_default=""),
            sa.Column("error_category", sa.String(64), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("resource_health"):
        op.create_table(
            "resource_health",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("resource_type", sa.String(32), nullable=False),
            sa.Column("resource_name", sa.String(255), nullable=False),
            sa.Column("namespace", sa.String(128), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("provider", sa.String(32), server_default=""),
            sa.Column("region", sa.String(32), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("summary", sa.String(512), server_default=""),
            sa.Column("check_type", sa.String(64), server_default=""),
            sa.Column("error_category", sa.String(64), server_default=""),
            sa.Column("desired", sa.Integer(), server_default="0"),
            sa.Column("ready", sa.Integer(), server_default="0"),
            sa.Column("available", sa.Integer(), server_default="0"),
            sa.Column("unavailable", sa.Integer(), server_default="0"),
            sa.Column("restart_count", sa.Integer(), server_default="0"),
            sa.Column("reason", sa.String(128), server_default=""),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_successful_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("cluster_id", "resource_type", "namespace", "resource_name", name="uq_resource_health_ref"),
        )
    if not _has_table("application_health"):
        op.create_table(
            "application_health",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("application_id", sa.String(128), nullable=False),
            sa.Column("application_name", sa.String(255), server_default=""),
            sa.Column("environment_id", sa.String(128), nullable=False),
            sa.Column("provider", sa.String(32), server_default=""),
            sa.Column("region", sa.String(32), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("summary", sa.String(512), server_default=""),
            sa.Column("likely_cause", sa.String(255), server_default=""),
            sa.Column("evidence_json", sa.Text(), server_default="[]"),
            sa.Column("correlation_json", sa.Text(), server_default="{}"),
            sa.Column("consecutive_unhealthy", sa.Integer(), server_default="0"),
            sa.Column("consecutive_healthy", sa.Integer(), server_default="0"),
            sa.Column("desired_replicas", sa.Integer(), server_default="0"),
            sa.Column("available_replicas", sa.Integer(), server_default="0"),
            sa.Column("crashloop", sa.Integer(), server_default="0"),
            sa.Column("failed_pods", sa.Integer(), server_default="0"),
            sa.Column("restart_count", sa.Integer(), server_default="0"),
            sa.Column("http_status", sa.String(16), server_default=""),
            sa.Column("ingress_status", sa.String(16), server_default=""),
            sa.Column("certificate_status", sa.String(16), server_default=""),
            sa.Column("pipeline_status", sa.String(32), server_default=""),
            sa.Column("deployment_status", sa.String(32), server_default=""),
            sa.Column("cluster_status", sa.String(16), server_default=""),
            sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_successful_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_category", sa.String(64), server_default=""),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("application_id", "environment_id", name="uq_application_health_scope"),
        )
    if not _has_table("health_incident"):
        op.create_table(
            "health_incident",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("provider", sa.String(32), server_default=""),
            sa.Column("region", sa.String(32), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("severity", sa.String(16), server_default="HIGH"),
            sa.Column("root_symptom", sa.String(255), server_default=""),
            sa.Column("affected_resources_json", sa.Text(), server_default="[]"),
            sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("acknowledged_by", sa.String(128), server_default=""),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_table("application_resource_mapping"):
        op.create_table(
            "application_resource_mapping",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("application_id", sa.String(128), nullable=False),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("namespace", sa.String(128), server_default=""),
            sa.Column("resource_type", sa.String(32), server_default=""),
            sa.Column("resource_name", sa.String(255), server_default=""),
            sa.Column("label_selector", sa.String(512), server_default=""),
            sa.Column("active", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("application_dependency"):
        op.create_table(
            "application_dependency",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("source_application_id", sa.String(128), nullable=False),
            sa.Column("dependency_type", sa.String(32), nullable=False),
            sa.Column("target_application_id", sa.String(128), server_default=""),
            sa.Column("external_name", sa.String(255), server_default=""),
            sa.Column("health_check_definition_id", sa.String(64), server_default=""),
            sa.Column("credential_ref", sa.String(256), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("health_alerts"):
        op.create_table(
            "health_alerts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("kind", sa.String(48), nullable=False),
            sa.Column("fingerprint", sa.String(64), nullable=False),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("severity", sa.String(16), server_default="HIGH"),
            sa.Column("status", sa.String(24), server_default="OPEN"),
            sa.Column("title", sa.String(255), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("fingerprint", name="uq_health_alert_fingerprint"),
        )
    if not _has_table("health_timeline_event"):
        op.create_table(
            "health_timeline_event",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("event_type", sa.String(48), nullable=False),
            sa.Column("title", sa.String(255), server_default=""),
            sa.Column("detail", sa.String(512), server_default=""),
            sa.Column("href", sa.String(512), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("health_audit_events"):
        op.create_table(
            "health_audit_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("object_name", sa.String(255), server_default=""),
            sa.Column("result", sa.String(32), server_default="succeeded"),
            sa.Column("detail", sa.Text(), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("health_scan_lock"):
        op.create_table(
            "health_scan_lock",
            sa.Column("environment_id", sa.String(128), primary_key=True),
            sa.Column("owner", sa.String(64), server_default=""),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    for name in (
        "health_scan_lock",
        "health_audit_events",
        "health_timeline_event",
        "health_alerts",
        "application_dependency",
        "application_resource_mapping",
        "health_incident",
        "application_health",
        "resource_health",
        "health_check_result",
        "health_check_definition",
    ):
        if _has_table(name):
            op.drop_table(name)
