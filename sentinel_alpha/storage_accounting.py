"""Deterministic logical-size accounting for canonical market observations.

This measures application-controlled payload growth rather than database file
allocation, which varies by engine, page size, indexes, WAL state, and vacuuming.
It stores no telemetry and never serializes secrets.
"""
from __future__ import annotations

import json

from sentinel_alpha.market_warehouse import ObservationInput


def canonical_observation_bytes(item: ObservationInput) -> int:
    """Return compact UTF-8 bytes required to reproduce the canonical payload."""
    payload = {
        "symbol": item.symbol.strip().upper(),
        "asset_type": item.asset_type.strip().lower(),
        "provider": item.provider.strip().upper(),
        "source_family": item.source_family.strip().upper(),
        "channel": item.channel.strip().lower(),
        "observed_at": item.observed_at.isoformat(),
        "ingested_at": item.ingested_at.isoformat(),
        "price": item.price,
        "source_record_id": item.source_record_id,
        "currency": item.currency.strip().upper(),
        "asset_name": item.asset_name,
        "quality_status": item.quality_status,
        "source_url": item.source_url,
        "metadata": item.metadata or {},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return len(encoded)
