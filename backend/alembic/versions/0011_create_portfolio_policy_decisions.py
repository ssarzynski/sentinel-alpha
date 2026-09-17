"""create portfolio policy decision ledger

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_policy_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_key", sa.String(length=36), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("compliant", sa.Boolean(), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("analytics_json", sa.JSON(), nullable=False),
        sa.Column("risk_json", sa.JSON(), nullable=True),
        sa.Column("findings_json", sa.JSON(), nullable=False),
        sa.Column("risk_data_status", sa.String(length=32), nullable=False),
        sa.Column("human_review_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("decision_key", name="uq_portfolio_policy_decision_key"),
    )
    for column in ("decision_key", "portfolio_id", "compliant", "risk_data_status", "human_review_status", "evaluated_at"):
        op.create_index(f"ix_portfolio_policy_decisions_{column}", "portfolio_policy_decisions", [column])


def downgrade() -> None:
    op.drop_table("portfolio_policy_decisions")
