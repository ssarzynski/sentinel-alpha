"""Deterministic macro-regime classification for Sentinel Alpha.

This layer is decision context only. It never produces a trade instruction.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Mapping

MACRO_RULE_VERSION = "macro-v1"


class MacroRegime(str, Enum):
    RISK_ON = "risk_on"
    NEUTRAL = "neutral"
    RISK_OFF = "risk_off"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MacroInput:
    metric: str
    value: float
    observed_at: datetime
    source: str
    max_age: timedelta

    def is_stale(self, now: datetime) -> bool:
        return _utc(now) - _utc(self.observed_at) > self.max_age


@dataclass(frozen=True)
class MacroRegimeResult:
    regime: MacroRegime
    score: int
    reasons: tuple[str, ...]
    stale_metrics: tuple[str, ...]
    missing_metrics: tuple[str, ...]
    evaluated_at: datetime
    rule_version: str = MACRO_RULE_VERSION

    @property
    def usable(self) -> bool:
        return self.regime is not MacroRegime.UNKNOWN


REQUIRED_METRICS = frozenset(
    {
        "fed_funds_rate",
        "treasury_2y",
        "treasury_10y",
        "inflation_yoy",
        "unemployment_rate",
        "volatility_index",
    }
)


def evaluate_macro_regime(
    inputs: Mapping[str, MacroInput], *, now: datetime | None = None
) -> MacroRegimeResult:
    """Classify market context using explicit, auditable thresholds.

    Missing, stale, or mislabeled critical data fails closed to UNKNOWN.
    """
    now = _utc(now or datetime.now(timezone.utc))
    mismatched = tuple(
        sorted(metric for metric, item in inputs.items() if metric != item.metric)
    )
    missing = tuple(sorted(REQUIRED_METRICS - set(inputs)))
    stale = tuple(
        sorted(
            name
            for name in REQUIRED_METRICS & set(inputs)
            if inputs[name].is_stale(now)
        )
    )
    if missing or stale or mismatched:
        reasons = []
        if missing:
            reasons.append("missing critical macro data: " + ", ".join(missing))
        if stale:
            reasons.append("stale critical macro data: " + ", ".join(stale))
        if mismatched:
            reasons.append("mislabeled macro data: " + ", ".join(mismatched))
        return MacroRegimeResult(MacroRegime.UNKNOWN, 0, tuple(reasons), stale, missing, now)

    two_year = inputs["treasury_2y"].value
    ten_year = inputs["treasury_10y"].value
    inflation = inputs["inflation_yoy"].value
    unemployment = inputs["unemployment_rate"].value
    volatility = inputs["volatility_index"].value
    fed_funds = inputs["fed_funds_rate"].value

    score = 0
    reasons: list[str] = []

    if ten_year < two_year:
        score -= 1
        reasons.append("2y/10y Treasury curve is inverted")
    else:
        score += 1
        reasons.append("2y/10y Treasury curve is not inverted")

    if volatility >= 30:
        score -= 2
        reasons.append("volatility is elevated")
    elif volatility <= 20:
        score += 1
        reasons.append("volatility is contained")

    if inflation >= 4:
        score -= 1
        reasons.append("inflation is elevated")
    elif inflation <= 2.5:
        score += 1
        reasons.append("inflation is near a lower range")

    if unemployment >= 6:
        score -= 1
        reasons.append("unemployment is elevated")
    elif unemployment <= 4.5:
        score += 1
        reasons.append("unemployment is relatively contained")

    if fed_funds >= 5:
        score -= 1
        reasons.append("policy rate is restrictive by initial rule threshold")

    if score >= 2:
        regime = MacroRegime.RISK_ON
    elif score <= -2:
        regime = MacroRegime.RISK_OFF
    else:
        regime = MacroRegime.NEUTRAL
    return MacroRegimeResult(regime, score, tuple(reasons), (), (), now)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
