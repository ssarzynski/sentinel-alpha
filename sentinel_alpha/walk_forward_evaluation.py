"""Out-of-sample evaluation for transparent historical conditions.

A condition is selected before each fold is evaluated. Training and later test
summaries are kept separate so Sentinel can measure whether an association
persists without using test outcomes to construct the training evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from sentinel_alpha.market_research import OutcomeSummary, summarize_outcomes
from sentinel_alpha.research_examples import ResearchExample
from sentinel_alpha.walk_forward import WalkForwardFold


@dataclass(frozen=True)
class FoldEvaluation:
    fold: int
    train_matches: int
    test_matches: int
    train: tuple[OutcomeSummary, ...]
    test: tuple[OutcomeSummary, ...]


def evaluate_condition_walk_forward(
    folds: Iterable[WalkForwardFold],
    *,
    condition: Callable[[ResearchExample], bool],
) -> tuple[FoldEvaluation, ...]:
    """Compare the same predeclared condition in training and unseen test data."""
    results: list[FoldEvaluation] = []
    for fold in folds:
        train_matches = tuple(item for item in fold.train if condition(item))
        test_matches = tuple(item for item in fold.test if condition(item))
        results.append(
            FoldEvaluation(
                fold=fold.fold,
                train_matches=len(train_matches),
                test_matches=len(test_matches),
                train=summarize_outcomes(train_matches),
                test=summarize_outcomes(test_matches),
            )
        )
    return tuple(results)
