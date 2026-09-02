"""phase4 aws topology

Revision ID: 0002_phase4_topology
Revises: 0001_phase3_aws
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_phase4_topology"
down_revision = "0001_phase3_aws"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cloud_providers",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
    )
    op.create_table(
        "platform_regions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider", sa.String(32), sa.ForeignKey("cloud_providers.id"), nullable=False),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("cloud_region", sa.String(64), nullable=False),
    )
    op.create_table(
        "cloud_accounts",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("platform_region", sa.String(32), nullable=False),
        sa.Column("cloud_region", sa.String(64), nullable=False),
        sa.Column("alias", sa.String(128), nullable=False),
        sa.Column("account_id", sa.String(32), nullable=False, server_default=""),
        sa.Column("role_arn", sa.String(512), nullable=False, server_default=""),
        sa.Column("external_id", sa.String(256), nullable=False, server_default=""),
        sa.Column("account_class", sa.String(32), nullable=False),
        sa.Column("readonly", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("session_name", sa.String(128), nullable=False, server_default=""),
        sa.Column("cluster_environment_tag", sa.String(64), nullable=False, server_default="Environment"),
        sa.UniqueConstraint("alias", name="uq_cloud_accounts_alias"),
    )
    op.create_table(
        "cloud_environments",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("account_id", sa.String(128), sa.ForeignKey("cloud_accounts.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("platform_region", sa.String(32), nullable=False),
        sa.Column("cloud_region", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("account_alias", sa.String(128), nullable=False),
        sa.Column("readonly", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("discovery_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_discovery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_certificate_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_error_class", sa.String(64), nullable=False, server_default=""),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
    )
    with op.batch_alter_table("eks_clusters") as batch:
        batch.add_column(sa.Column("environment_id", sa.String(128), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("eks_clusters") as batch:
        batch.drop_column("environment_id")
    op.drop_table("cloud_environments")
    op.drop_table("cloud_accounts")
    op.drop_table("platform_regions")
    op.drop_table("cloud_providers")
