"""durable market backfill runs

Revision ID: 0002_backfill_runs
Revises: 0001_market_warehouse
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_backfill_runs"
down_revision = "0001_market_warehouse"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_backfill_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("checkpoint_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed", sa.Integer(), nullable=False),
        sa.Column("inserted", sa.Integer(), nullable=False),
        sa.Column("existing", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.UniqueConstraint("provider", "symbol", "channel", name="uq_market_backfill_stream"),
    )
    op.create_index("ix_market_backfill_status", "market_backfill_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_market_backfill_status", table_name="market_backfill_runs")
    op.drop_table("market_backfill_runs")
