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
) -> ResearchDataset:
    """Build a bounded dataset from one ordered point-in-time history snapshot."""
    # Local import avoids a module cycle while retaining ResearchDataset as the
    # stable public return type.
    from sentinel_alpha.research_snapshot import build_research_dataset_snapshot

    return build_research_dataset_snapshot(
        warehouse,
        symbol,
        dataset_known_by=dataset_known_by,
        horizons=horizons,
        min_history=min_history,
        max_examples=max_examples,
    )
