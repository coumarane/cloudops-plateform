"""phase9 provider-neutral pipelines

Revision ID: 0007_phase9_pipelines
Revises: 0006_phase8_github
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_phase9_pipelines"
down_revision = "0006_phase8_github"
branch_labels = None
depends_on = None


def _inspector():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def upgrade() -> None:
    if not _has_table("pipeline_providers"):
        op.create_table(
            "pipeline_providers",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("key", sa.String(32), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("organization", sa.String(128), server_default=""),
            sa.Column("project", sa.String(128), server_default=""),
            sa.Column("base_url", sa.String(255), server_default=""),
            sa.Column("auth_ref", sa.String(512), server_default=""),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("status", sa.String(32), server_default="pending"),
            sa.Column("last_attempted_sync_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), server_default=""),
            sa.Column("last_error_class", sa.String(64), server_default=""),
            sa.Column("metadata_json", sa.Text(), server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("key", name="uq_pipeline_providers_key"),
        )
    if not _has_table("pipelines"):
        op.create_table(
            "pipelines",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("provider_id", sa.String(64), sa.ForeignKey("pipeline_providers.id"), nullable=False),
            sa.Column("external_id", sa.String(128), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("repository_id", sa.String(64), server_default=""),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("default_branch", sa.String(128), server_default=""),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.Column("metadata_json", sa.Text(), server_default="{}"),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("provider_id", "external_id", name="uq_pipelines_provider_external"),
        )
    if not _has_table("pipeline_runs"):
        op.create_table(
            "pipeline_runs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("pipeline_id", sa.String(64), sa.ForeignKey("pipelines.id"), nullable=False),
            sa.Column("external_run_id", sa.String(128), nullable=False),
            sa.Column("branch", sa.String(255), server_default=""),
            sa.Column("commit_sha", sa.String(64), server_default=""),
            sa.Column("version", sa.String(128), server_default=""),
            sa.Column("trigger", sa.String(64), server_default=""),
            sa.Column("actor", sa.String(128), server_default=""),
            sa.Column("status", sa.String(32), server_default="UNKNOWN"),
            sa.Column("provider_status", sa.String(64), server_default=""),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("external_url", sa.String(512), server_default=""),
            sa.Column("environment_id", sa.String(128), server_default=""),
            sa.Column("deployment_id", sa.String(128), server_default=""),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("repository_id", sa.String(64), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("metadata_json", sa.Text(), server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("pipeline_id", "external_run_id", name="uq_pipeline_runs_external"),
        )
    if not _has_table("pipeline_stages"):
        op.create_table(
            "pipeline_stages",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("run_id", sa.String(64), sa.ForeignKey("pipeline_runs.id"), nullable=False),
            sa.Column("external_id", sa.String(128), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), server_default="UNKNOWN"),
            sa.Column("provider_status", sa.String(64), server_default=""),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0"),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.UniqueConstraint("run_id", "external_id", name="uq_pipeline_stages_external"),
        )
    if not _has_table("pipeline_jobs"):
        op.create_table(
            "pipeline_jobs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("run_id", sa.String(64), sa.ForeignKey("pipeline_runs.id"), nullable=False),
            sa.Column("stage_id", sa.String(64), server_default=""),
            sa.Column("external_id", sa.String(128), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), server_default="UNKNOWN"),
            sa.Column("provider_status", sa.String(64), server_default=""),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.UniqueConstraint("run_id", "external_id", name="uq_pipeline_jobs_external"),
        )
    if not _has_table("pipeline_environment_mapping"):
        op.create_table(
            "pipeline_environment_mapping",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("pipeline_id", sa.String(64), sa.ForeignKey("pipelines.id"), nullable=False),
            sa.Column("environment_id", sa.String(128), nullable=False),
            sa.Column("branch_pattern", sa.String(128), server_default="*"),
            sa.Column("stage_name", sa.String(128), server_default=""),
            sa.Column("active", sa.Boolean(), server_default=sa.true()),
            sa.Column("priority", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "pipeline_id",
                "environment_id",
                "branch_pattern",
                "stage_name",
                name="uq_pipeline_env_mapping",
            ),
        )
    if not _has_table("pipeline_application_mapping"):
        op.create_table(
            "pipeline_application_mapping",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("pipeline_id", sa.String(64), sa.ForeignKey("pipelines.id"), nullable=False),
            sa.Column("application_id", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("pipeline_id", "application_id", name="uq_pipeline_app_mapping"),
        )
    if not _has_table("pipeline_webhook_deliveries"):
        op.create_table(
            "pipeline_webhook_deliveries",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("delivery_id", sa.String(128), nullable=False),
            sa.Column("provider_key", sa.String(32), nullable=False),
            sa.Column("event", sa.String(64), server_default=""),
            sa.Column("payload_digest", sa.String(64), server_default=""),
            sa.Column("payload_json", sa.Text(), server_default=""),
            sa.Column("status", sa.String(32), server_default="queued"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("delivery_id", name="uq_pipeline_webhook_delivery"),
        )
    if not _has_table("pipeline_audit_events"):
        op.create_table(
            "pipeline_audit_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("object_name", sa.String(255), server_default=""),
            sa.Column("pipeline_id", sa.String(64), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("result", sa.String(32), server_default="succeeded"),
            sa.Column("detail", sa.Text(), server_default=""),
            sa.Column("correlation_id", sa.String(64), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("pipeline_alerts"):
        op.create_table(
            "pipeline_alerts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("kind", sa.String(48), nullable=False),
            sa.Column("run_id", sa.String(64), server_default=""),
            sa.Column("pipeline_id", sa.String(64), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("severity", sa.String(16), server_default="MEDIUM"),
            sa.Column("status", sa.String(24), server_default="OPEN"),
            sa.Column("title", sa.String(255), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    for name in (
        "pipeline_alerts",
        "pipeline_audit_events",
        "pipeline_webhook_deliveries",
        "pipeline_application_mapping",
        "pipeline_environment_mapping",
        "pipeline_jobs",
        "pipeline_stages",
        "pipeline_runs",
        "pipelines",
        "pipeline_providers",
    ):
        if _has_table(name):
            op.drop_table(name)
