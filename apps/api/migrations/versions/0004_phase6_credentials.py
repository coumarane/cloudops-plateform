"""phase6 credentials and secret metadata

Revision ID: 0004_phase6_credentials
Revises: 0003_phase5_alibaba
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_phase6_credentials"
down_revision = "0003_phase5_alibaba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("platform_jobs") as batch:
        batch.add_column(sa.Column("target_id", sa.String(128), nullable=False, server_default=""))

    op.create_table(
        "credentials",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("platform_region", sa.String(32), nullable=False),
        sa.Column("account_alias", sa.String(128), nullable=False),
        sa.Column("account_id", sa.String(32), nullable=False, server_default=""),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("environment_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("credential_type", sa.String(64), nullable=False),
        sa.Column("secret_backend", sa.String(32), nullable=False),
        sa.Column("secret_reference", sa.String(512), nullable=False, server_default=""),
        sa.Column("fingerprint", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="HEALTHY"),
        sa.Column("rotation_policy_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotation_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(128), nullable=False, server_default=""),
        sa.Column("role_arn", sa.String(512), nullable=False, server_default=""),
        sa.Column("external_id_ref", sa.String(256), nullable=False, server_default=""),
        sa.Column("cloud_region", sa.String(64), nullable=False, server_default=""),
        sa.Column("extra_json", sa.Text(), nullable=False, server_default="{}"),
        sa.UniqueConstraint(
            "provider",
            "platform_region",
            "account_alias",
            "environment",
            "name",
            name="uq_credentials_scope_name",
        ),
    )
    op.create_table(
        "credential_versions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("credential_id", sa.String(64), sa.ForeignKey("credentials.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False, server_default=""),
        sa.Column("secret_reference", sa.String(512), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False, server_default=""),
    )
    op.create_table(
        "credential_validations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("credential_id", sa.String(64), sa.ForeignKey("credentials.id"), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_category", sa.String(64), nullable=False, server_default=""),
        sa.Column("provider_account", sa.String(64), nullable=False, server_default=""),
        sa.Column("correlation_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "credential_rotation_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("credential_id", sa.String(64), sa.ForeignKey("credentials.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("actor", sa.String(128), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "credential_audit_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("credential_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("credential_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default=""),
        sa.Column("platform_region", sa.String(32), nullable=False, server_default=""),
        sa.Column("account_alias", sa.String(128), nullable=False, server_default=""),
        sa.Column("environment", sa.String(32), nullable=False, server_default=""),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("change_ticket", sa.String(128), nullable=False, server_default=""),
        sa.Column("correlation_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("credential_audit_events")
    op.drop_table("credential_rotation_events")
    op.drop_table("credential_validations")
    op.drop_table("credential_versions")
    op.drop_table("credentials")
    with op.batch_alter_table("platform_jobs") as batch:
        batch.drop_column("target_id")
