"""Adapters from verified provider payloads into the canonical market warehouse."""
from __future__ import annotations

from datetime import datetime, timezone

from sentinel_alpha.alpha_vantage_ingestion import DailyEquityBar
from sentinel_alpha.market_warehouse import MarketWarehouse, ObservationInput


def ingest_alpha_vantage_daily(
    warehouse: MarketWarehouse,
    bar: DailyEquityBar,
    *,
    ingested_at: datetime | None = None,
):
    """Persist one Alpha Vantage daily close without changing provider acquisition code."""
    received = ingested_at or datetime.now(timezone.utc)
    record_id = f"{bar.symbol.upper()}:{bar.observed_at.date().isoformat()}:daily-close"
    return warehouse.ingest(
        ObservationInput(
            symbol=bar.symbol,
            asset_type="equity",
            provider="ALPHA_VANTAGE",
            source_family="EQUITY_MARKET",
            channel="daily",
            observed_at=bar.observed_at,
            ingested_at=received,
            price=bar.close,
            source_record_id=record_id,
            metadata={
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "volume": bar.volume,
                "interval": "1d",
            },
        )
    )
