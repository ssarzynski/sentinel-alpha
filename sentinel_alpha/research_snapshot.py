"""Single-snapshot research dataset construction.

This optimized path reads warehouse history once, then constructs feature and
outcome records in memory. It must remain behaviorally equivalent to the
reference dataset builder before replacing it.
"""
from __future__ import annotations

from datetime import datetime
from math import sqrt
from statistics import pstdev

from sentinel_alpha.market_features import MarketFeatures
from sentinel_alpha.market_outcomes import ForwardOutcome
from sentinel_alpha.market_warehouse import MarketWarehouse
from sentinel_alpha.research_dataset import ResearchDataset
from sentinel_alpha.research_examples import ResearchExample
from sentinel_alpha.time_utils import as_utc


def _change(current: float, previous: float) -> float | None:
    return None if previous == 0 else current / previous - 1.0


def build_research_dataset_snapshot(
    warehouse: MarketWarehouse,
    symbol: str,
    *,
    dataset_known_by: datetime,
    horizons: tuple[int, ...] = (5, 20, 60),
    min_history: int = 6,
    max_examples: int = 5000,
) -> ResearchDataset:
    """Build a bounded research dataset from one ordered warehouse snapshot."""
    if min_history < 1:
        raise ValueError("min_history must be positive")
    if max_examples < 1 or max_examples > 50000:
        raise ValueError("max_examples must be between 1 and 50000")
    if not horizons or any(h < 1 for h in horizons):
        raise ValueError("horizons must contain positive observation counts")
    cutoff = as_utc(dataset_known_by)
    if cutoff is None:
        raise ValueError("dataset_known_by is required")
    normalized = symbol.strip().upper()
    rows = warehouse.history(normalized, known_by=cutoff)
    examples: list[ResearchExample] = []
    skipped = 0

    for index, anchor in enumerate(rows):
        if index + 1 < min_history:
            skipped += 1
            continue
        if len(examples) >= max_examples:
            break
        feature_cutoff = as_utc(anchor.ingested_at)
        anchor_time = as_utc(anchor.observed_at)
        if feature_cutoff is None or anchor_time is None or feature_cutoff < anchor_time:
            skipped += 1
            continue
        known_rows = [row for row in rows[: index + 1] if as_utc(row.ingested_at) <= feature_cutoff]
        if not known_rows or as_utc(known_rows[-1].observed_at) != anchor_time:
            skipped += 1
            continue
        closes = [float(row.price) for row in known_rows]
        one = _change(closes[-1], closes[-2]) if len(closes) >= 2 else None
        five = _change(closes[-1], closes[-6]) if len(closes) >= 6 else None
        returns = [_change(c, p) for c, p in zip(closes[-5:], closes[-6:-1])] if len(closes) >= 6 else []
        valid_returns = [value for value in returns if value is not None]
        volatility = pstdev(valid_returns) * sqrt(252) if len(valid_returns) == 5 else None
        volumes = [(row.metadata_json or {}).get("volume") for row in known_rows[-2:]]
        volume_change = None
        if len(volumes) == 2 and volumes[0] is not None and volumes[1] is not None:
            volume_change = _change(float(volumes[1]), float(volumes[0]))
        trend = _change(closes[-1], sum(closes[-5:]) / 5) if len(closes) >= 5 else None
        features = MarketFeatures(normalized, anchor.observed_at, len(known_rows), closes[-1], one, five, volatility, volume_change, trend)

        outcomes = []
        for horizon in horizons:
            target_index = index + horizon
            if target_index >= len(rows):
                outcomes.append(ForwardOutcome(normalized, anchor.observed_at, float(anchor.price), horizon, None, None, None))
            else:
                target = rows[target_index]
                outcome_return = _change(float(target.price), float(anchor.price))
                outcomes.append(ForwardOutcome(normalized, anchor.observed_at, float(anchor.price), horizon, target.observed_at, float(target.price), outcome_return))
        examples.append(ResearchExample(normalized, anchor_time, feature_cutoff, cutoff, features, tuple(outcomes)))

    return ResearchDataset(normalized, cutoff, tuple(examples), skipped)
