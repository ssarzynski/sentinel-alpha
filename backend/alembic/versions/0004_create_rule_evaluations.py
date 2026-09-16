"""create rule evaluations table

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rule_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evaluation_key", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("asset", sa.String(length=32), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("independent_confirmation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("facts_json", sa.JSON(), nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("evidence_categories_json", sa.JSON(), nullable=False),
        sa.Column("source_families_json", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("evaluation_key", name="uq_rule_evaluations_key"),
    )
    op.create_index("ix_rule_evaluations_evaluation_key", "rule_evaluations", ["evaluation_key"])
    op.create_index("ix_rule_evaluations_rule_id", "rule_evaluations", ["rule_id"])
    op.create_index("ix_rule_evaluations_asset", "rule_evaluations", ["asset"])
    op.create_index("ix_rule_evaluations_evaluated_at", "rule_evaluations", ["evaluated_at"])


def downgrade() -> None:
    op.drop_index("ix_rule_evaluations_evaluated_at", table_name="rule_evaluations")
    op.drop_index("ix_rule_evaluations_asset", table_name="rule_evaluations")
    op.drop_index("ix_rule_evaluations_rule_id", table_name="rule_evaluations")
    op.drop_index("ix_rule_evaluations_evaluation_key", table_name="rule_evaluations")
    op.drop_table("rule_evaluations")
