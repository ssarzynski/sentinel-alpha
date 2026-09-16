from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecFiling(Base):
    __tablename__ = "sec_filings"
    __table_args__ = (UniqueConstraint("accession_number", name="uq_sec_filings_accession"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), index=True)
    ticker: Mapped[str | None] = mapped_column(String(16), index=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    accession_number: Mapped[str] = mapped_column(String(32), nullable=False)
    form: Mapped[str] = mapped_column(String(20), index=True)
    filing_date: Mapped[date] = mapped_column(Date, index=True)
    report_date: Mapped[date | None] = mapped_column(Date)
    primary_document: Mapped[str] = mapped_column(String(255))
    filing_url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="SEC_EDGAR", nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Evidence(Base):
    """Append-only normalized evidence. Application services must never update rows in place."""

    __tablename__ = "evidence"
    __table_args__ = (UniqueConstraint("evidence_key", name="uq_evidence_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_key: Mapped[str] = mapped_column(String(128), nullable=False)
    asset: Mapped[str | None] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_family: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
