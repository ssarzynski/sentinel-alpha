"""create evidence table

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_key", sa.String(length=128), nullable=False),
        sa.Column("asset", sa.String(length=32), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_family", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("evidence_key", name="uq_evidence_key"),
    )
    op.create_index("ix_evidence_asset", "evidence", ["asset"])
    op.create_index("ix_evidence_category", "evidence", ["category"])
    op.create_index("ix_evidence_source", "evidence", ["source"])
    op.create_index("ix_evidence_observed_at", "evidence", ["observed_at"])


def downgrade() -> None:
    op.drop_index("ix_evidence_observed_at", table_name="evidence")
    op.drop_index("ix_evidence_source", table_name="evidence")
    op.drop_index("ix_evidence_category", table_name="evidence")
    op.drop_index("ix_evidence_asset", table_name="evidence")
    op.drop_table("evidence")
