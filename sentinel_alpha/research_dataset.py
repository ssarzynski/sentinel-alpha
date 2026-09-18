"""Bounded multi-anchor historical research dataset generation.

The public builder delegates to the verified single-snapshot implementation so
research construction remains constant-query and avoids redundant database work.
No research dataset is persisted here: canonical observations remain the source
of truth and derived examples are recomputed when needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel_alpha.market_warehouse import MarketWarehouse
    from sentinel_alpha.research_examples import ResearchExample
    from sentinel_alpha.resource_metrics import ResourceMetrics


@dataclass(frozen=True)
class ResearchDataset:
    symbol: str
    dataset_known_by: datetime
    examples: tuple["ResearchExample", ...]
    skipped: int


def build_research_dataset(
    warehouse: "MarketWarehouse",
    symbol: str,
    *,
    dataset_known_by: datetime,
    horizons: tuple[int, ...] = (5, 20, 60),
    min_history: int = 6,
    max_examples: int = 5000,
    metrics: "ResourceMetrics | None" = None,
) -> ResearchDataset:
    """Build a bounded dataset and optionally report compact usage counters."""
    from sentinel_alpha.research_snapshot import build_research_dataset_snapshot

    dataset = build_research_dataset_snapshot(
        warehouse,
        symbol,
        dataset_known_by=dataset_known_by,
        horizons=horizons,
        min_history=min_history,
        max_examples=max_examples,
    )
    if metrics is not None:
        # Snapshot construction performs one history query. Derived examples are
        # ephemeral, so they intentionally contribute zero persistent bytes.
        metrics.record_sql(1)
        metrics.record_records(len(dataset.examples))
    return dataset
