"""phase8 GitHub integration

Revision ID: 0006_phase8_github
Revises: 0005_phase7_certificates
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_phase8_github"
down_revision = "0005_phase7_certificates"
branch_labels = None
depends_on = None


def _inspector():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def upgrade() -> None:
    if not _has_table("github_integrations"):
        op.create_table(
            "github_integrations",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("app_id", sa.String(64), nullable=False),
            sa.Column("installation_id", sa.String(64), nullable=False),
            sa.Column("organization", sa.String(128), nullable=False, server_default=""),
            sa.Column("api_url", sa.String(255), nullable=False, server_default="https://api.github.com"),
            sa.Column("private_key_ref", sa.String(512), nullable=False),
            sa.Column("webhook_secret_ref", sa.String(512), server_default=""),
            sa.Column("status", sa.String(32), server_default="pending"),
            sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), server_default=""),
            sa.Column("last_error_class", sa.String(64), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("github_organizations"):
        op.create_table(
            "github_organizations",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("integration_id", sa.String(64), sa.ForeignKey("github_integrations.id"), nullable=False),
            sa.Column("github_id", sa.String(64), nullable=False),
            sa.Column("login", sa.String(128), nullable=False),
            sa.Column("name", sa.String(255), server_default=""),
            sa.Column("avatar_url", sa.String(512), server_default=""),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.Column("status", sa.String(32), server_default="ok"),
            sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_table("github_repositories"):
        op.create_table(
            "github_repositories",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("organization_id", sa.String(64), sa.ForeignKey("github_organizations.id"), nullable=False),
            sa.Column("github_id", sa.String(64), nullable=False),
            sa.Column("organization", sa.String(128), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), server_default=""),
            sa.Column("default_branch", sa.String(128), server_default="main"),
            sa.Column("visibility", sa.String(32), server_default="private"),
            sa.Column("archived", sa.Boolean(), server_default=sa.false()),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("github_id", name="uq_github_repositories_github_id"),
        )
    if not _has_table("github_application_repositories"):
        op.create_table(
            "github_application_repositories",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("repository_id", sa.String(64), sa.ForeignKey("github_repositories.id"), nullable=False),
            sa.Column("application_id", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("repository_id", "application_id", name="uq_github_app_repo"),
        )
    if not _has_table("github_environment_mapping"):
        op.create_table(
            "github_environment_mapping",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("github_repository_id", sa.String(64), sa.ForeignKey("github_repositories.id"), nullable=False),
            sa.Column("github_environment", sa.String(128), nullable=False),
            sa.Column("cloudops_environment_id", sa.String(128), nullable=False),
            sa.Column("active", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("github_repository_id", "github_environment", name="uq_github_env_mapping"),
        )
    if not _has_table("github_workflows"):
        op.create_table(
            "github_workflows",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("repository_id", sa.String(64), sa.ForeignKey("github_repositories.id"), nullable=False),
            sa.Column("github_id", sa.String(64), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("path", sa.String(512), server_default=""),
            sa.Column("state", sa.String(32), server_default="active"),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("github_id", name="uq_github_workflows_github_id"),
        )
    if not _has_table("github_workflow_runs"):
        op.create_table(
            "github_workflow_runs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("workflow_id", sa.String(64), sa.ForeignKey("github_workflows.id"), nullable=False),
            sa.Column("repository_id", sa.String(64), sa.ForeignKey("github_repositories.id"), nullable=False),
            sa.Column("github_id", sa.String(64), nullable=False),
            sa.Column("branch", sa.String(255), server_default=""),
            sa.Column("commit_sha", sa.String(64), server_default=""),
            sa.Column("event", sa.String(64), server_default=""),
            sa.Column("actor", sa.String(128), server_default=""),
            sa.Column("github_status", sa.String(32), server_default=""),
            sa.Column("github_conclusion", sa.String(32), server_default=""),
            sa.Column("status", sa.String(32), server_default="UNKNOWN"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("run_attempt", sa.Integer(), server_default="1"),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.Column("github_environment", sa.String(128), server_default=""),
            sa.Column("cloudops_environment_id", sa.String(128), server_default=""),
            sa.Column("application_id", sa.String(128), server_default=""),
            sa.Column("deployment_id", sa.String(128), server_default=""),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.UniqueConstraint("github_id", name="uq_github_workflow_runs_github_id"),
        )
    if not _has_table("github_workflow_jobs"):
        op.create_table(
            "github_workflow_jobs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("run_id", sa.String(64), sa.ForeignKey("github_workflow_runs.id"), nullable=False),
            sa.Column("github_id", sa.String(64), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("github_status", sa.String(32), server_default=""),
            sa.Column("github_conclusion", sa.String(32), server_default=""),
            sa.Column("status", sa.String(32), server_default="UNKNOWN"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("runner_name", sa.String(128), server_default=""),
            sa.Column("runner_type", sa.String(128), server_default=""),
            sa.Column("html_url", sa.String(512), server_default=""),
            sa.UniqueConstraint("github_id", name="uq_github_workflow_jobs_github_id"),
        )
    if not _has_table("github_variables"):
        op.create_table(
            "github_variables",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("repository_id", sa.String(64), sa.ForeignKey("github_repositories.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("scope", sa.String(32), nullable=False, server_default="repository"),
            sa.Column("github_environment", sa.String(128), server_default=""),
            sa.Column("organization", sa.String(128), server_default=""),
            sa.Column("value_masked", sa.String(64), server_default="••••••••••••"),
            sa.Column("sensitive", sa.Boolean(), server_default=sa.false()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cloudops_environment_id", sa.String(128), server_default=""),
            sa.UniqueConstraint("repository_id", "name", "scope", "github_environment", name="uq_github_variables"),
        )
    if not _has_table("github_secrets"):
        op.create_table(
            "github_secrets",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("repository_id", sa.String(64), sa.ForeignKey("github_repositories.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("scope", sa.String(32), nullable=False, server_default="repository"),
            sa.Column("github_environment", sa.String(128), server_default=""),
            sa.Column("organization", sa.String(128), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cloudops_environment_id", sa.String(128), server_default=""),
            sa.UniqueConstraint("repository_id", "name", "scope", "github_environment", name="uq_github_secrets"),
        )
    if not _has_table("github_webhook_deliveries"):
        op.create_table(
            "github_webhook_deliveries",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("delivery_id", sa.String(128), nullable=False),
            sa.Column("event", sa.String(64), nullable=False),
            sa.Column("action", sa.String(64), server_default=""),
            sa.Column("payload_digest", sa.String(64), server_default=""),
            sa.Column("payload_json", sa.Text(), server_default=""),
            sa.Column("status", sa.String(32), server_default="queued"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("delivery_id", name="uq_github_webhook_delivery"),
        )
    if not _has_table("github_audit_events"):
        op.create_table(
            "github_audit_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("action", sa.String(64), nullable=False, index=True),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("object_name", sa.String(255), server_default=""),
            sa.Column("repository_id", sa.String(64), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("result", sa.String(32), server_default="succeeded"),
            sa.Column("detail", sa.Text(), server_default=""),
            sa.Column("correlation_id", sa.String(64), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("github_alerts"):
        op.create_table(
            "github_alerts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("kind", sa.String(48), nullable=False),
            sa.Column("run_id", sa.String(64), server_default=""),
            sa.Column("repository_id", sa.String(64), server_default=""),
            sa.Column("workflow_id", sa.String(64), server_default=""),
            sa.Column("environment", sa.String(32), server_default=""),
            sa.Column("severity", sa.String(16), server_default="MEDIUM"),
            sa.Column("status", sa.String(24), server_default="OPEN"),
            sa.Column("title", sa.String(255), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    for table in (
        "github_alerts",
        "github_audit_events",
        "github_webhook_deliveries",
        "github_secrets",
        "github_variables",
        "github_workflow_jobs",
        "github_workflow_runs",
        "github_workflows",
        "github_environment_mapping",
        "github_application_repositories",
        "github_repositories",
        "github_organizations",
        "github_integrations",
    ):
        if _has_table(table):
            op.drop_table(table)
