"""create prediction outcomes table

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("target_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_price", sa.Float(), nullable=False),
        sa.Column("asset_return", sa.Float(), nullable=False),
        sa.Column("benchmark_asset", sa.String(length=32), nullable=True),
        sa.Column("benchmark_reference_price", sa.Float(), nullable=True),
        sa.Column("benchmark_observed_price", sa.Float(), nullable=True),
        sa.Column("benchmark_return", sa.Float(), nullable=True),
        sa.Column("excess_return", sa.Float(), nullable=True),
        sa.Column("direction_correct", sa.Boolean(), nullable=False),
        sa.Column("price_source", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("prediction_id", "horizon_days", name="uq_prediction_outcome_horizon"),
    )
    op.create_index("ix_prediction_outcomes_prediction_id", "prediction_outcomes", ["prediction_id"])
    op.create_index("ix_prediction_outcomes_horizon_days", "prediction_outcomes", ["horizon_days"])
    op.create_index("ix_prediction_outcomes_created_at", "prediction_outcomes", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_prediction_outcomes_created_at", table_name="prediction_outcomes")
    op.drop_index("ix_prediction_outcomes_horizon_days", table_name="prediction_outcomes")
    op.drop_index("ix_prediction_outcomes_prediction_id", table_name="prediction_outcomes")
    op.drop_table("prediction_outcomes")
