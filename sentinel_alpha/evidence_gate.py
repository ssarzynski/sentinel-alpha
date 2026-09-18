"""Minimum-evidence gates for research findings.

This gate does not rank assets or produce trade signals. It prevents sparse or
unstable historical associations from silently flowing into future model work.
"""
from __future__ import annotations

from dataclasses import dataclass

from sentinel_alpha.stability_report import HorizonStability


@dataclass(frozen=True)
class EvidencePolicy:
    min_test_folds: int = 3
    min_test_samples: int = 30
    min_direction_agreement: float = 0.60
    min_effect_retention: float = 0.25


@dataclass(frozen=True)
class EvidenceDecision:
    horizon: int
    sufficient: bool
    reasons: tuple[str, ...]


def evaluate_evidence(item: HorizonStability, policy: EvidencePolicy = EvidencePolicy()) -> EvidenceDecision:
    if policy.min_test_folds < 1 or policy.min_test_samples < 1:
        raise ValueError("minimum folds and samples must be positive")
    if not 0 <= policy.min_direction_agreement <= 1:
        raise ValueError("min_direction_agreement must be between 0 and 1")
    if policy.min_effect_retention < 0:
        raise ValueError("min_effect_retention cannot be negative")

    reasons: list[str] = []
    if item.folds_with_test_evidence < policy.min_test_folds:
        reasons.append("too_few_test_folds")
    if item.test_sample_size < policy.min_test_samples:
        reasons.append("too_few_test_samples")
    if item.direction_agreement_rate is None or item.direction_agreement_rate < policy.min_direction_agreement:
        reasons.append("unstable_direction")
    if item.effect_retention is None or item.effect_retention < policy.min_effect_retention:
        reasons.append("insufficient_effect_retention")
    return EvidenceDecision(item.horizon, not reasons, tuple(reasons))
