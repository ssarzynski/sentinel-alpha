from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, Text, UniqueConstraint, func
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


class RuleEvaluation(Base):
    __tablename__ = "rule_evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_key: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    asset: Mapped[str | None] = mapped_column(String(32), index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    independent_confirmation_count: Mapped[int] = mapped_column(default=0, nullable=False)
    facts_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    conditions_json: Mapped[list] = mapped_column(JSON, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, nullable=False)
    evidence_categories_json: Mapped[list] = mapped_column(JSON, nullable=False)
    source_families_json: Mapped[list] = mapped_column(JSON, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_key: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    asset: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reference_price: Mapped[float] = mapped_column(Float, nullable=False)
    reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    market_regime: Mapped[str | None] = mapped_column(String(64))
    rule_evaluation_ids_json: Mapped[list] = mapped_column(JSON, nullable=False)
    evidence_ids_json: Mapped[list] = mapped_column(JSON, nullable=False)
    human_review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    thesis_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"
    __table_args__ = (UniqueConstraint("prediction_id", "horizon_days", name="uq_prediction_outcome_horizon"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_price: Mapped[float] = mapped_column(Float, nullable=False)
    asset_return: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark_asset: Mapped[str | None] = mapped_column(String(32))
    benchmark_reference_price: Mapped[float | None] = mapped_column(Float)
    benchmark_observed_price: Mapped[float | None] = mapped_column(Float)
    benchmark_return: Mapped[float | None] = mapped_column(Float)
    excess_return: Mapped[float | None] = mapped_column(Float)
    direction_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    price_source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ResearchJournalEntry(Base):
    """Versioned research artifact. Prior versions are never overwritten."""
    __tablename__ = "research_journal_entries"
    __table_args__ = (UniqueConstraint("research_key", "version", name="uq_research_journal_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    research_key: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    methodology_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    linked_evidence_ids_json: Mapped[list] = mapped_column(JSON, nullable=False)
    linked_prediction_ids_json: Mapped[list] = mapped_column(JSON, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    results_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    limitations_json: Mapped[list] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    decision: Mapped[str | None] = mapped_column(String(32), index=True)
    production_rule_change_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (UniqueConstraint("run_key", name="uq_ingestion_runs_run_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    run_key: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_existing: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failures_json: Mapped[list] = mapped_column(JSON, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("portfolio_key", name="uq_portfolios_portfolio_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_key: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, index=True)
    policy_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    __table_args__ = (UniqueConstraint("portfolio_id", "asset", name="uq_portfolio_position_asset"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    asset: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    cost_basis: Mapped[float | None] = mapped_column(Float)
    mark_price: Mapped[float] = mapped_column(Float, nullable=False)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    price_source: Mapped[str] = mapped_column(String(64), nullable=False)
    price_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
