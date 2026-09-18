"""Predeclared, bounded research trials for real historical market data.

The trial plan is intentionally small to limit API/compute cost and reduce
researcher degrees of freedom. It defines hypotheses before results are seen.
No ranking, recommendation, trade execution, or model fitting occurs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sentinel_alpha.research_examples import ResearchExample


@dataclass(frozen=True)
class TrialHypothesis:
    name: str
    condition: Callable[[ResearchExample], bool]


@dataclass(frozen=True)
class ResearchTrialPlan:
    symbols: tuple[str, ...]
    horizons: tuple[int, ...]
    hypotheses: tuple[TrialHypothesis, ...]
    max_symbols: int = 4
    max_hypotheses: int = 3

    def validate(self) -> None:
        if not self.symbols or len(self.symbols) > self.max_symbols:
            raise ValueError("trial symbol count exceeds bounded plan")
        if not self.hypotheses or len(self.hypotheses) > self.max_hypotheses:
            raise ValueError("trial hypothesis count exceeds bounded plan")
        if not self.horizons or any(h < 1 for h in self.horizons):
            raise ValueError("trial horizons must be positive")
        if len(set(self.symbols)) != len(self.symbols):
            raise ValueError("trial symbols must be unique")
        if len({item.name for item in self.hypotheses}) != len(self.hypotheses):
            raise ValueError("trial hypothesis names must be unique")


def _positive_trend(item: ResearchExample) -> bool:
    value = item.features.trend_5
    return value is not None and value > 0


def _negative_trend(item: ResearchExample) -> bool:
    value = item.features.trend_5
    return value is not None and value < 0


def _positive_five_period_return(item: ResearchExample) -> bool:
    value = item.features.return_5
    return value is not None and value > 0


FIRST_REAL_DATA_TRIAL = ResearchTrialPlan(
    # Start with supported equity/index-like symbols. Crypto is intentionally
    # deferred until its acquisition adapter is verified rather than forcing
    # unlike provider schemas through the equity path.
    symbols=("NVDA", "SPY"),
    horizons=(5, 20, 60),
    hypotheses=(
        TrialHypothesis("positive_5_period_trend", _positive_trend),
        TrialHypothesis("negative_5_period_trend", _negative_trend),
        TrialHypothesis("positive_5_period_return", _positive_five_period_return),
    ),
)
