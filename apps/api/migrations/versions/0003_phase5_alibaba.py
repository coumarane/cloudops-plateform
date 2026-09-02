"""phase5 alibaba china

Revision ID: 0003_phase5_alibaba
Revises: 0002_phase4_topology
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_phase5_alibaba"
down_revision = "0002_phase4_topology"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cloud_accounts") as batch:
        batch.add_column(sa.Column("credential_ref", sa.String(256), nullable=False, server_default=""))
        batch.add_column(sa.Column("credential_fingerprint", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("validation_status", sa.String(32), nullable=False, server_default=""))
    with op.batch_alter_table("eks_clusters") as batch:
        batch.add_column(sa.Column("cluster_type", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("extra_json", sa.Text(), nullable=False, server_default="{}"))
    with op.batch_alter_table("eks_cluster_health") as batch:
        batch.add_column(sa.Column("stateful_set_unhealthy_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("ingress_unhealthy_count", sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("acm_certificates") as batch:
        batch.add_column(sa.Column("cluster_name", sa.String(255), nullable=False, server_default=""))
        batch.add_column(sa.Column("namespace", sa.String(255), nullable=False, server_default=""))
        batch.add_column(sa.Column("source", sa.String(32), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("acm_certificates") as batch:
        batch.drop_column("source")
        batch.drop_column("namespace")
        batch.drop_column("cluster_name")
    with op.batch_alter_table("eks_cluster_health") as batch:
        batch.drop_column("ingress_unhealthy_count")
        batch.drop_column("stateful_set_unhealthy_count")
    with op.batch_alter_table("eks_clusters") as batch:
        batch.drop_column("extra_json")
        batch.drop_column("cluster_type")
    with op.batch_alter_table("cloud_accounts") as batch:
        batch.drop_column("validation_status")
        batch.drop_column("last_validated_at")
        batch.drop_column("credential_fingerprint")
        batch.drop_column("credential_ref")
