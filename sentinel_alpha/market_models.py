"""Canonical point-in-time market warehouse models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentinel_alpha.database import Base


class MarketAsset(Base):
    __tablename__ = "market_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    observations: Mapped[list["MarketObservation"]] = relationship(back_populates="asset")


class MarketSource(Base):
    __tablename__ = "market_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_family: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="market")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("provider", "source_family", "channel", name="uq_market_source_identity"),)


class MarketObservation(Base):
    __tablename__ = "market_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("market_assets.id", ondelete="RESTRICT"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("market_sources.id", ondelete="RESTRICT"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    asset: Mapped[MarketAsset] = relationship(back_populates="observations")
    source: Mapped[MarketSource] = relationship()

    __table_args__ = (
        UniqueConstraint("source_id", "source_record_id", name="uq_market_observation_provider_record"),
        Index("ix_market_observation_asset_time", "asset_id", "observed_at"),
        Index("ix_market_observation_ingested_time", "ingested_at"),
    )
