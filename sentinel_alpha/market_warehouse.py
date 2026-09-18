"""Controlled read/write boundary for canonical market observations.

The service owns normalization, idempotent ingestion, and point-in-time reads.
It deliberately contains no prediction, scoring, portfolio, or trading logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from sentinel_alpha.market_models import MarketAsset, MarketObservation, MarketSource


@dataclass(frozen=True)
class ObservationInput:
    symbol: str
    asset_type: str
    provider: str
    source_family: str
    channel: str
    observed_at: datetime
    ingested_at: datetime
    price: float
    source_record_id: str
    currency: str = "USD"
    asset_name: str | None = None
    quality_status: str = "accepted"
    source_url: str | None = None
    metadata: dict | None = None


class MarketWarehouse:
    """Application boundary around the canonical market warehouse."""

    def __init__(self, session: Session):
        self.session = session

    def ingest(self, item: ObservationInput) -> tuple[MarketObservation, bool]:
        """Insert once by provider record identity; return (row, created)."""
        source = self._source(item)
        existing = self.session.scalar(
            select(MarketObservation).where(
                MarketObservation.source_id == source.id,
                MarketObservation.source_record_id == item.source_record_id,
            )
        )
        if existing is not None:
            return existing, False

        asset = self._asset(item)
        observation = MarketObservation(
            asset_id=asset.id,
            source_id=source.id,
            observed_at=item.observed_at,
            ingested_at=item.ingested_at,
            price=item.price,
            source_record_id=item.source_record_id,
            quality_status=item.quality_status,
            source_url=item.source_url,
            metadata_json=item.metadata or {},
        )
        self.session.add(observation)
        self.session.flush()
        return observation, True

    def history(
        self,
        symbol: str,
        *,
        known_by: datetime | None = None,
        observed_from: datetime | None = None,
        observed_to: datetime | None = None,
    ) -> list[MarketObservation]:
        """Read chronologically, optionally restricting data to what was known by a time."""
        stmt = (
            select(MarketObservation)
            .join(MarketAsset)
            .where(MarketAsset.symbol == self._normalize_symbol(symbol))
        )
        if known_by is not None:
            stmt = stmt.where(MarketObservation.ingested_at <= known_by)
        if observed_from is not None:
            stmt = stmt.where(MarketObservation.observed_at >= observed_from)
        if observed_to is not None:
            stmt = stmt.where(MarketObservation.observed_at <= observed_to)
        stmt = stmt.order_by(MarketObservation.observed_at, MarketObservation.id)
        return list(self.session.scalars(stmt))

    def _asset(self, item: ObservationInput) -> MarketAsset:
        symbol = self._normalize_symbol(item.symbol)
        asset = self.session.scalar(select(MarketAsset).where(MarketAsset.symbol == symbol))
        if asset is None:
            asset = MarketAsset(
                symbol=symbol,
                asset_type=item.asset_type.strip().lower(),
                name=item.asset_name,
                currency=item.currency.strip().upper(),
                created_at=item.ingested_at,
            )
            self.session.add(asset)
            self.session.flush()
        return asset

    def _source(self, item: ObservationInput) -> MarketSource:
        provider = item.provider.strip().upper()
        family = item.source_family.strip().upper()
        channel = item.channel.strip().lower()
        source = self.session.scalar(
            select(MarketSource).where(
                MarketSource.provider == provider,
                MarketSource.source_family == family,
                MarketSource.channel == channel,
            )
        )
        if source is None:
            source = MarketSource(
                provider=provider,
                source_family=family,
                channel=channel,
                created_at=item.ingested_at,
            )
            self.session.add(source)
            self.session.flush()
        return source

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol is required")
        return normalized
