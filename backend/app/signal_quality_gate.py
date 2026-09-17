from __future__ import annotations

from dataclasses import dataclass

from app.data_quality_gate import DataQualityGate


@dataclass(frozen=True)
class SignalGateResult:
    requested_level: str
    effective_level: str
    allowed: bool
    reasons: tuple[str, ...]


def gate_signal_level(
    requested_level: str,
    *,
    independent_evidence_confirmations: int,
    market_quality: DataQualityGate,
) -> SignalGateResult:
    """Apply Sentinel Alpha confirmation controls to an alert level.

    STRONG alerts require at least two independent evidence confirmations and a
    market-quality PASS/DEGRADED state that still permits risk signals. A failed
    prerequisite withholds the strong alert instead of silently weakening the
    rule. This function never creates or executes a financial order.
    """
    level = requested_level.strip().upper()
    reasons: list[str] = []

    if level != "STRONG":
        return SignalGateResult(level, level, True, ())

    if independent_evidence_confirmations < 2:
        reasons.append("fewer_than_two_independent_evidence_confirmations")
    if not market_quality.risk_signals_allowed:
        reasons.append(f"market_data_{market_quality.status.lower()}")

    if reasons:
        return SignalGateResult(level, "WITHHELD", False, tuple(reasons))
    return SignalGateResult(level, "STRONG", True, ())
