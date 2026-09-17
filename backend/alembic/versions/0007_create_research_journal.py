"""create research journal

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_key", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("methodology_json", sa.JSON(), nullable=False),
        sa.Column("linked_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("linked_prediction_ids_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("limitations_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("production_rule_change_authorized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("research_key", "version", name="uq_research_journal_version"),
    )
    op.create_index("ix_research_journal_entries_research_key", "research_journal_entries", ["research_key"])
    op.create_index("ix_research_journal_entries_status", "research_journal_entries", ["status"])
    op.create_index("ix_research_journal_entries_decision", "research_journal_entries", ["decision"])
    op.create_index("ix_research_journal_entries_created_at", "research_journal_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_research_journal_entries_created_at", table_name="research_journal_entries")
    op.drop_index("ix_research_journal_entries_decision", table_name="research_journal_entries")
    op.drop_index("ix_research_journal_entries_status", table_name="research_journal_entries")
    op.drop_index("ix_research_journal_entries_research_key", table_name="research_journal_entries")
    op.drop_table("research_journal_entries")
