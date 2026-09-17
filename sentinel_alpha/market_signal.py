"""Versioned deterministic market-signal classification.

Raw market observations never become SUPPORT by themselves. A caller must
supply a current bar plus an explicit historical baseline, and every rule must
pass before the market provider can contribute one independent confirmation.
"""

from dataclasses import dataclass

from .alpha_vantage_ingestion import DailyEquityBar, daily_bar_to_records
from .evidence_roles import ClassifiedEvidence, EvidenceRole

MARKET_SIGNAL_RULE_VERSION = "market-v1"
MIN_MOMENTUM_RETURN = 0.02
MIN_VOLUME_RATIO = 1.50


@dataclass(frozen=True)
class MarketBaseline:
    """Historical inputs computed without using the current bar."""

    prior_close: float
    average_volume: float

    def validate(self) -> None:
        if self.prior_close <= 0:
            raise ValueError("prior_close must be positive")
        if self.average_volume <= 0:
            raise ValueError("average_volume must be positive")


@dataclass(frozen=True)
class MarketSignalResult:
    rule_version: str
    momentum_return: float
    volume_ratio: float
    qualifies: bool
    evidence: tuple[ClassifiedEvidence, ...]


def classify_daily_bar(bar: DailyEquityBar, baseline: MarketBaseline) -> MarketSignalResult:
    """Classify a daily equity bar using the fixed market-v1 rule.

    market-v1 requires BOTH:
    - close >= 2% above the prior close; and
    - volume >= 1.5x the historical average volume.

    Price and volume records share one Alpha Vantage independence group, so a
    qualifying result can contribute at most one provider confirmation.
    """
    baseline.validate()
    momentum_return = (bar.close / baseline.prior_close) - 1.0
    volume_ratio = bar.volume / baseline.average_volume
    qualifies = momentum_return >= MIN_MOMENTUM_RETURN and volume_ratio >= MIN_VOLUME_RATIO
    role = EvidenceRole.SUPPORT if qualifies else EvidenceRole.CONTEXT
    rationale = (
        f"{MARKET_SIGNAL_RULE_VERSION}: momentum={momentum_return:.6f}, "
        f"volume_ratio={volume_ratio:.6f}; "
        f"requires momentum>={MIN_MOMENTUM_RETURN:.6f} and volume_ratio>={MIN_VOLUME_RATIO:.6f}"
    )
    evidence = tuple(
        ClassifiedEvidence(record, role, rationale) for record in daily_bar_to_records(bar)
    )
    return MarketSignalResult(
        rule_version=MARKET_SIGNAL_RULE_VERSION,
        momentum_return=momentum_return,
        volume_ratio=volume_ratio,
        qualifies=qualifies,
        evidence=evidence,
    )
