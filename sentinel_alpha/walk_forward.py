"""Chronological walk-forward validation primitives.

These utilities preserve time order so research is evaluated on later unseen
examples. They perform no model fitting, asset ranking, recommendation, or trade.
"""
from __future__ import annotations

from dataclasses import dataclass

from sentinel_alpha.research_dataset import ResearchDataset
from sentinel_alpha.research_examples import ResearchExample


@dataclass(frozen=True)
class WalkForwardFold:
    fold: int
    train: tuple[ResearchExample, ...]
    test: tuple[ResearchExample, ...]

    @property
    def train_end(self):
        return self.train[-1].anchor_at

    @property
    def test_start(self):
        return self.test[0].anchor_at


def walk_forward_splits(
    dataset: ResearchDataset,
    *,
    min_train: int = 100,
    test_size: int = 20,
    step: int | None = None,
    max_folds: int = 50,
) -> tuple[WalkForwardFold, ...]:
    """Create expanding-window train/test folds without temporal overlap."""
    if min_train < 1:
        raise ValueError("min_train must be positive")
    if test_size < 1:
        raise ValueError("test_size must be positive")
    stride = test_size if step is None else step
    if stride < 1:
        raise ValueError("step must be positive")
    if not 1 <= max_folds <= 500:
        raise ValueError("max_folds must be between 1 and 500")

    examples = tuple(sorted(dataset.examples, key=lambda item: item.anchor_at))
    folds: list[WalkForwardFold] = []
    train_end = min_train
    while train_end + test_size <= len(examples) and len(folds) < max_folds:
        train = examples[:train_end]
        test = examples[train_end : train_end + test_size]
        if train[-1].anchor_at >= test[0].anchor_at:
            raise ValueError("walk-forward split contains temporal overlap")
        folds.append(WalkForwardFold(len(folds) + 1, train, test))
        train_end += stride
    return tuple(folds)
