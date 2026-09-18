"""Build leakage-resistant feature/outcome research examples.

A research example keeps the information available at a historical decision time
separate from labels that became observable only later. It is not a prediction,
recommendation, or trading instruction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sentinel_alpha.market_features import MarketFeatures, extract_market_features
from sentinel_alpha.market_outcomes import ForwardOutcome, label_forward_outcomes
from sentinel_alpha.market_warehouse import MarketWarehouse
from sentinel_alpha.time_utils import as_utc


@dataclass(frozen=True)
class ResearchExample:
    symbol: str
    anchor_at: datetime
    feature_known_by: datetime
    dataset_known_by: datetime
    features: MarketFeatures
    outcomes: tuple[ForwardOutcome, ...]


def build_research_example(
    warehouse: MarketWarehouse,
    symbol: str,
    *,
    anchor_at: datetime,
    feature_known_by: datetime,
    dataset_known_by: datetime,
    horizons: tuple[int, ...] = (5, 20, 60),
) -> ResearchExample:
    """Join point-in-time features to later research labels without leakage.

    ``feature_known_by`` is the hard information boundary for explanatory
    variables. ``dataset_known_by`` may be later so realized outcomes can be
    labeled, but it is never passed into feature extraction.
    """
    anchor = as_utc(anchor_at)
    feature_cutoff = as_utc(feature_known_by)
    dataset_cutoff = as_utc(dataset_known_by)
    if anchor is None or feature_cutoff is None or dataset_cutoff is None:
        raise ValueError("research timestamps are required")
    if feature_cutoff < anchor:
        raise ValueError("feature_known_by cannot precede anchor_at")
    if dataset_cutoff < feature_cutoff:
        raise ValueError("dataset_known_by cannot precede feature_known_by")

    features = extract_market_features(warehouse, symbol, known_by=feature_cutoff)
    if features.as_of is None or as_utc(features.as_of) != anchor:
        raise ValueError("anchor must be the latest observation available at feature time")

    outcomes = tuple(
        label_forward_outcomes(
            warehouse,
            symbol,
            anchor_at=anchor,
            horizons=horizons,
            dataset_known_by=dataset_cutoff,
        )
    )
    return ResearchExample(
        symbol=symbol.strip().upper(),
        anchor_at=anchor,
        feature_known_by=feature_cutoff,
        dataset_known_by=dataset_cutoff,
        features=features,
        outcomes=outcomes,
    )
