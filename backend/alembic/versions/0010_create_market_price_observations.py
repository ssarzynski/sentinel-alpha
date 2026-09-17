"""create market price observations

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_price_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_family", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="accepted"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("asset", "source", "source_record_id", name="uq_market_price_source_record"),
    )
    for column in ("asset", "observed_at", "source", "source_family", "quality_status", "ingested_at"):
        op.create_index(f"ix_market_price_observations_{column}", "market_price_observations", [column])


def downgrade() -> None:
    op.drop_table("market_price_observations")
