"""create sec filings table

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sec_filings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cik", sa.String(length=10), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("accession_number", sa.String(length=32), nullable=False),
        sa.Column("form", sa.String(length=20), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("primary_document", sa.String(length=255), nullable=False),
        sa.Column("filing_url", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="SEC_EDGAR"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("accession_number", name="uq_sec_filings_accession"),
    )
    op.create_index("ix_sec_filings_cik", "sec_filings", ["cik"])
    op.create_index("ix_sec_filings_ticker", "sec_filings", ["ticker"])
    op.create_index("ix_sec_filings_form", "sec_filings", ["form"])
    op.create_index("ix_sec_filings_filing_date", "sec_filings", ["filing_date"])


def downgrade() -> None:
    op.drop_index("ix_sec_filings_filing_date", table_name="sec_filings")
    op.drop_index("ix_sec_filings_form", table_name="sec_filings")
    op.drop_index("ix_sec_filings_ticker", table_name="sec_filings")
    op.drop_index("ix_sec_filings_cik", table_name="sec_filings")
    op.drop_table("sec_filings")
