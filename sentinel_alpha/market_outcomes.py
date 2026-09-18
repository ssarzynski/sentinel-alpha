"""Historical forward-outcome labeling for research.

Outcomes describe what happened after a historical anchor. They are research
labels only and must never be included in a feature vector available at that
anchor time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sentinel_alpha.market_warehouse import MarketWarehouse


@dataclass(frozen=True)
class ForwardOutcome:
    symbol: str
    anchor_at: datetime
    anchor_price: float
    horizon: int
    outcome_at: datetime | None
    outcome_price: float | None
    forward_return: float | None


def _as_utc(value: datetime) -> datetime:
    """Normalize provider/database timestamps before identity comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def label_forward_outcomes(
    warehouse: MarketWarehouse,
    symbol: str,
    *,
    anchor_at: datetime,
    horizons: tuple[int, ...] = (5, 20, 60),
    dataset_known_by: datetime,
) -> list[ForwardOutcome]:
    """Label N-observation forward returns from a historical anchor.

    ``dataset_known_by`` limits which records may be used to construct the
    research dataset, preserving ingestion provenance even for backfilled data.
    Horizons are observation counts, not calendar days.
    """
    if not horizons or any(horizon < 1 for horizon in horizons):
        raise ValueError("horizons must contain positive observation counts")
    rows = warehouse.history(symbol, known_by=dataset_known_by)
    normalized_anchor = _as_utc(anchor_at)
    anchor_index = next(
        (index for index, row in enumerate(rows) if _as_utc(row.observed_at) == normalized_anchor),
        None,
    )
    if anchor_index is None:
        raise ValueError("anchor observation is not available in the research dataset")
    anchor = rows[anchor_index]
    results = []
    for horizon in horizons:
        target_index = anchor_index + horizon
        if target_index >= len(rows):
            results.append(
                ForwardOutcome(
                    symbol.strip().upper(),
                    anchor.observed_at,
                    float(anchor.price),
                    horizon,
                    None,
                    None,
                    None,
                )
            )
            continue
        target = rows[target_index]
        forward_return = (
            None if anchor.price == 0 else float(target.price) / float(anchor.price) - 1.0
        )
        results.append(
            ForwardOutcome(
                symbol.strip().upper(),
                anchor.observed_at,
                float(anchor.price),
                horizon,
                target.observed_at,
                float(target.price),
                forward_return,
            )
        )
    return results
