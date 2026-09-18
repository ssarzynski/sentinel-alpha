"""canonical market warehouse

Revision ID: 0001_market_warehouse
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_market_warehouse"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("symbol"),
    )
    op.create_table(
        "market_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source_family", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "source_family", "channel", name="uq_market_source_identity"),
    )
    op.create_table(
        "market_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("market_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("market_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("source_id", "source_record_id", name="uq_market_observation_provider_record"),
    )
    op.create_index("ix_market_observation_asset_time", "market_observations", ["asset_id", "observed_at"])
    op.create_index("ix_market_observation_ingested_time", "market_observations", ["ingested_at"])


def downgrade() -> None:
    op.drop_index("ix_market_observation_ingested_time", table_name="market_observations")
    op.drop_index("ix_market_observation_asset_time", table_name="market_observations")
    op.drop_table("market_observations")
    op.drop_table("market_sources")
    op.drop_table("market_assets")
