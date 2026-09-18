"""Bounded multi-anchor historical research dataset generation.

This module expands verified warehouse history into leakage-resistant research
examples. It deliberately performs no model fitting, ranking, or trading action.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sentinel_alpha.market_warehouse import MarketWarehouse
from sentinel_alpha.research_examples import ResearchExample, build_research_example
from sentinel_alpha.time_utils import as_utc


@dataclass(frozen=True)
class ResearchDataset:
    symbol: str
    dataset_known_by: datetime
    examples: tuple[ResearchExample, ...]
    skipped: int


def build_research_dataset(
    warehouse: MarketWarehouse,
    symbol: str,
    *,
    dataset_known_by: datetime,
    horizons: tuple[int, ...] = (5, 20, 60),
    min_history: int = 6,
    max_examples: int = 5000,
) -> ResearchDataset:
    """Build examples across historical anchors using each anchor's own cutoff.

    An anchor's feature cutoff is the observation's original ingestion time, not
    the later dataset construction time. Anchors without enough prior history or
    whose latest-known observation does not align cleanly are skipped.
    """
    if min_history < 1:
        raise ValueError("min_history must be positive")
    if max_examples < 1 or max_examples > 50000:
        raise ValueError("max_examples must be between 1 and 50000")
    cutoff = as_utc(dataset_known_by)
    if cutoff is None:
        raise ValueError("dataset_known_by is required")
    rows = warehouse.history(symbol, known_by=cutoff)
    examples: list[ResearchExample] = []
    skipped = 0
    for index, row in enumerate(rows):
        if index + 1 < min_history:
            skipped += 1
            continue
        if len(examples) >= max_examples:
            break
        try:
            example = build_research_example(
                warehouse,
                symbol,
                anchor_at=row.observed_at,
                feature_known_by=row.ingested_at,
                dataset_known_by=cutoff,
                horizons=horizons,
            )
        except ValueError:
            skipped += 1
            continue
        examples.append(example)
    return ResearchDataset(symbol.strip().upper(), cutoff, tuple(examples), skipped)
