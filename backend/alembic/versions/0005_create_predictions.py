"""create predictions table

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_key", sa.String(length=36), nullable=False),
        sa.Column("asset", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reference_price", sa.Float(), nullable=False),
        sa.Column("reference_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_regime", sa.String(length=64), nullable=True),
        sa.Column("rule_evaluation_ids_json", sa.JSON(), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("human_review_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("thesis_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("prediction_key", name="uq_predictions_key"),
    )
    for name, cols in [
        ("ix_predictions_prediction_key", ["prediction_key"]),
        ("ix_predictions_asset", ["asset"]),
        ("ix_predictions_reference_time", ["reference_time"]),
        ("ix_predictions_human_review_status", ["human_review_status"]),
        ("ix_predictions_created_at", ["created_at"]),
    ]:
        op.create_index(name, "predictions", cols)


def downgrade() -> None:
    for name in ["ix_predictions_created_at", "ix_predictions_human_review_status", "ix_predictions_reference_time", "ix_predictions_asset", "ix_predictions_prediction_key"]:
        op.drop_index(name, table_name="predictions")
    op.drop_table("predictions")
