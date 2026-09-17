"""create portfolios and positions

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_key", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("base_currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("portfolio_key", name="uq_portfolios_portfolio_key"),
    )
    op.create_index("ix_portfolios_portfolio_key", "portfolios", ["portfolio_key"])
    op.create_index("ix_portfolios_status", "portfolios", ["status"])
    op.create_index("ix_portfolios_owner_user_id", "portfolios", ["owner_user_id"])
    op.create_index("ix_portfolios_created_at", "portfolios", ["created_at"])

    op.create_table(
        "portfolio_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("asset", sa.String(length=32), nullable=False),
        sa.Column("asset_class", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("cost_basis", sa.Float(), nullable=True),
        sa.Column("mark_price", sa.Float(), nullable=False),
        sa.Column("market_value", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("price_source", sa.String(length=64), nullable=False),
        sa.Column("price_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("portfolio_id", "asset", name="uq_portfolio_position_asset"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_portfolio_positions_portfolio_id", "portfolio_positions", ["portfolio_id"])
    op.create_index("ix_portfolio_positions_asset", "portfolio_positions", ["asset"])
    op.create_index("ix_portfolio_positions_asset_class", "portfolio_positions", ["asset_class"])
    op.create_index("ix_portfolio_positions_price_observed_at", "portfolio_positions", ["price_observed_at"])
    op.create_index("ix_portfolio_positions_updated_at", "portfolio_positions", ["updated_at"])


def downgrade() -> None:
    op.drop_table("portfolio_positions")
    op.drop_table("portfolios")
