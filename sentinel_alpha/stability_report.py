"""Aggregate walk-forward evidence without turning it into a trade signal."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from sentinel_alpha.walk_forward_evaluation import FoldEvaluation


@dataclass(frozen=True)
class HorizonStability:
    horizon: int
    folds_with_test_evidence: int
    test_sample_size: int
    direction_agreement_rate: float | None
    mean_train_return: float | None
    mean_test_return: float | None
    effect_retention: float | None


def summarize_stability(evaluations: tuple[FoldEvaluation, ...]) -> tuple[HorizonStability, ...]:
    """Summarize persistence by horizon; missing evidence remains missing."""
    horizons = sorted({summary.horizon for item in evaluations for summary in (*item.train, *item.test)})
    output: list[HorizonStability] = []
    for horizon in horizons:
        pairs = []
        test_n = 0
        for item in evaluations:
            train = next((x for x in item.train if x.horizon == horizon), None)
            test = next((x for x in item.test if x.horizon == horizon), None)
            if train is None or test is None or train.mean_return is None or test.mean_return is None:
                continue
            pairs.append((train.mean_return, test.mean_return))
            test_n += test.sample_size
        if not pairs:
            output.append(HorizonStability(horizon, 0, 0, None, None, None, None))
            continue
        train_mean = mean(x[0] for x in pairs)
        test_mean = mean(x[1] for x in pairs)
        agreement = sum((a > 0) == (b > 0) for a, b in pairs) / len(pairs)
        retention = None if train_mean == 0 else test_mean / train_mean
        output.append(HorizonStability(horizon, len(pairs), test_n, agreement, train_mean, test_mean, retention))
    return tuple(output)
