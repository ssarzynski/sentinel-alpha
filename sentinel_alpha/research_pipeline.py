"""Thin end-to-end orchestration for controlled market research.

This composes existing verified components. It does not fit models, rank assets,
issue recommendations, or place trades.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from sentinel_alpha.evidence_gate import EvidenceDecision, EvidencePolicy, evaluate_evidence
from sentinel_alpha.research_dataset import ResearchDataset, build_research_dataset
from sentinel_alpha.research_examples import ResearchExample
from sentinel_alpha.research_registry import ResearchCandidate, ResearchRegistry
from sentinel_alpha.resource_metrics import ResourceMetrics
from sentinel_alpha.stability_report import HorizonStability, summarize_stability
from sentinel_alpha.walk_forward import walk_forward_splits
from sentinel_alpha.walk_forward_evaluation import evaluate_condition_walk_forward


@dataclass(frozen=True)
class ResearchPipelineResult:
    symbol: str
    hypothesis: str
    examples: int
    folds: int
    stability: tuple[HorizonStability, ...]
    decisions: tuple[EvidenceDecision, ...]
    candidates: tuple[ResearchCandidate, ...]
    resources: dict[str, int]


def _preserve_requested_horizons(
    stability: tuple[HorizonStability, ...], horizons: tuple[int, ...]
) -> tuple[HorizonStability, ...]:
    """Return one stability record per requested horizon, failing closed if absent."""
    by_horizon = {item.horizon: item for item in stability}
    return tuple(
        by_horizon.get(
            horizon,
            HorizonStability(horizon, 0, 0, None, None, None, None),
        )
        for horizon in horizons
    )


def run_research_pipeline(
    warehouse,
    symbol: str,
    *,
    hypothesis: str,
    condition: Callable[[ResearchExample], bool],
    dataset_known_by: datetime,
    horizons: tuple[int, ...] = (5, 20, 60),
    min_history: int = 6,
    min_train: int = 100,
    test_size: int = 20,
    policy: EvidencePolicy = EvidencePolicy(),
    registry: ResearchRegistry | None = None,
) -> ResearchPipelineResult:
    """Run one bounded hypothesis through the complete validation chain."""
    metrics = ResourceMetrics()
    dataset: ResearchDataset = build_research_dataset(
        warehouse, symbol, dataset_known_by=dataset_known_by,
        horizons=horizons, min_history=min_history, metrics=metrics,
    )
    folds = walk_forward_splits(dataset, min_train=min_train, test_size=test_size)
    evaluations = evaluate_condition_walk_forward(folds, condition=condition)
    stability = _preserve_requested_horizons(summarize_stability(evaluations), horizons)
    decisions = tuple(evaluate_evidence(item, policy) for item in stability)
    active_registry = registry if registry is not None else ResearchRegistry()
    candidates = tuple(active_registry.record(hypothesis, decision) for decision in decisions)
    return ResearchPipelineResult(
        symbol.strip().upper(), " ".join(hypothesis.strip().split()), len(dataset.examples),
        len(folds), stability, decisions, candidates, metrics.snapshot(),
    )
