"""Transparent statistical summaries over historical research examples.

This layer measures associations in completed historical labels. It does not
predict, rank assets, recommend trades, or infer causation.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean, median, stdev
from typing import Callable, Iterable

from sentinel_alpha.research_examples import ResearchExample


@dataclass(frozen=True)
class OutcomeSummary:
    horizon: int
    sample_size: int
    mean_return: float | None
    median_return: float | None
    positive_rate: float | None
    standard_deviation: float | None
    standard_error: float | None


def summarize_outcomes(
    examples: Iterable[ResearchExample],
    *,
    condition: Callable[[ResearchExample], bool] | None = None,
) -> tuple[OutcomeSummary, ...]:
    """Summarize realized returns by horizon for examples matching a condition.

    Missing/unrealized labels are excluded rather than treated as zero. Standard
    error is descriptive sampling uncertainty, not a guarantee of future results.
    """
    selected = [example for example in examples if condition is None or condition(example)]
    by_horizon: dict[int, list[float]] = {}
    for example in selected:
        for outcome in example.outcomes:
            if outcome.forward_return is not None:
                by_horizon.setdefault(outcome.horizon, []).append(float(outcome.forward_return))

    summaries = []
    for horizon in sorted(by_horizon):
        values = by_horizon[horizon]
        n = len(values)
        dispersion = stdev(values) if n >= 2 else None
        summaries.append(
            OutcomeSummary(
                horizon=horizon,
                sample_size=n,
                mean_return=mean(values),
                median_return=median(values),
                positive_rate=sum(value > 0 for value in values) / n,
                standard_deviation=dispersion,
                standard_error=(dispersion / sqrt(n)) if dispersion is not None else None,
            )
        )
    return tuple(summaries)
