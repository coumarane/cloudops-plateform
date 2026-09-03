"""phase11.5 platform administration and real data activation

Revision ID: 0010_phase11_5_platform_admin
Revises: 0009_phase11_alerting
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0010_phase11_5_platform_admin"
down_revision = "0009_phase11_alerting"
branch_labels = None
depends_on = None


def _inspector():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _has_column(table: str, column: str) -> bool:
    return any(item["name"] == column for item in _inspector().get_columns(table))


def _add(table: str, column: str, col) -> None:
    if _has_table(table) and not _has_column(table, column):
        op.add_column(table, col)


def upgrade() -> None:
    _add("cloud_accounts", "managed_provider_id", sa.Column("managed_provider_id", sa.String(64), server_default=""))
    _add("cloud_accounts", "enabled", sa.Column("enabled", sa.Boolean(), server_default=sa.true()))
    _add("cloud_accounts", "display_name", sa.Column("display_name", sa.String(128), server_default=""))
    _add("cloud_accounts", "description", sa.Column("description", sa.String(255), server_default=""))
    _add("cloud_accounts", "auth_strategy", sa.Column("auth_strategy", sa.String(32), server_default=""))
    _add("cloud_accounts", "ram_role", sa.Column("ram_role", sa.String(512), server_default=""))
    _add("cloud_accounts", "cloud_regions_json", sa.Column("cloud_regions_json", sa.Text(), server_default="[]"))
    _add("cloud_accounts", "last_error_class", sa.Column("last_error_class", sa.String(64), server_default=""))
    _add("cloud_accounts", "identity_account", sa.Column("identity_account", sa.String(64), server_default=""))
    _add("cloud_accounts", "identity_principal", sa.Column("identity_principal", sa.String(255), server_default=""))
    _add("cloud_environments", "name", sa.Column("name", sa.String(128), server_default=""))
    _add("cloud_environments", "code", sa.Column("code", sa.String(64), server_default=""))
    _add("cloud_environments", "description", sa.Column("description", sa.String(255), server_default=""))
    _add("cloud_environments", "readiness_status", sa.Column("readiness_status", sa.String(32), server_default="NOT_CONFIGURED"))
    _add("eks_clusters", "ignored", sa.Column("ignored", sa.Boolean(), server_default=sa.false()))
    _add("eks_clusters", "monitoring_enabled", sa.Column("monitoring_enabled", sa.Boolean(), server_default=sa.true()))
    _add("platform_jobs", "resources_found", sa.Column("resources_found", sa.Integer(), server_default="0"))
    _add("platform_jobs", "error_count", sa.Column("error_count", sa.Integer(), server_default="0"))
    if not _has_table("managed_providers"):
        op.create_table(
            "managed_providers",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("provider_type", sa.String(32), nullable=False),
            sa.Column("description", sa.String(255), server_default=""),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("auth_strategy", sa.String(32), server_default=""),
            sa.Column("status", sa.String(32), server_default="NOT_CONFIGURED"),
            sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("validation_status", sa.String(32), server_default=""),
            sa.Column("error_category", sa.String(64), server_default=""),
            sa.Column("identity_account", sa.String(64), server_default=""),
            sa.Column("identity_principal", sa.String(255), server_default=""),
            sa.Column("extra_json", sa.Text(), server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("managed_applications"):
        op.create_table(
            "managed_applications",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("description", sa.String(255), server_default=""),
            sa.Column("owner_team", sa.String(128), server_default=""),
            sa.Column("repository_id", sa.String(128), server_default=""),
            sa.Column("pipeline_id", sa.String(128), server_default=""),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
            sa.Column("extra_json", sa.Text(), server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("application_environment_bindings"):
        op.create_table(
            "application_environment_bindings",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("application_id", sa.String(64), sa.ForeignKey("managed_applications.id"), nullable=False),
            sa.Column("environment_id", sa.String(128), nullable=False),
            sa.Column("cluster_id", sa.String(128), server_default=""),
            sa.Column("namespace", sa.String(255), server_default=""),
            sa.Column("workload", sa.String(255), server_default=""),
            sa.Column("health_endpoint", sa.String(512), server_default=""),
        )
    if not _has_table("platform_settings"):
        op.create_table(
            "platform_settings",
            sa.Column("key", sa.String(128), primary_key=True),
            sa.Column("value", sa.Text(), server_default=""),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_by", sa.String(128), server_default=""),
        )
    if not _has_table("platform_audit_events"):
        op.create_table(
            "platform_audit_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("object_name", sa.String(255), server_default=""),
            sa.Column("result", sa.String(32), server_default="succeeded"),
            sa.Column("detail", sa.Text(), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    return None
