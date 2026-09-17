"""End-to-end Sentinel Alpha evaluation pipeline."""

from dataclasses import dataclass

from .decision_engine import Decision, evaluate_signal
from .models import Signal
from .provenance import NormalizedRecord, independent_confirmation_keys
from .risk_gate import RiskGateResult, TradeProposal, evaluate_risk_gate


@dataclass(frozen=True)
class EvaluationResult:
    signal: Signal
    decision: Decision
    risk: RiskGateResult


def evaluate_records(
    *,
    asset: str,
    status: str,
    records: list[NormalizedRecord],
    proposal: TradeProposal,
    new_entries_this_week: int,
    conflicts: list[str] | None = None,
) -> EvaluationResult:
    """Evaluate normalized evidence through confirmation and risk controls.

    This function is intentionally pure: it does not trade, persist state, or
    authorize execution. It produces a reviewable decision for a human.
    """
    confirmation_keys = sorted(independent_confirmation_keys(records))
    evidence = [record.evidence for record in records]
    signal = Signal(
        asset=asset.strip().upper(),
        status=status,
        confirmations=confirmation_keys,
        conflicts=list(conflicts or []),
        evidence=evidence,
    )
    decision = evaluate_signal(signal)
    risk = evaluate_risk_gate(
        decision,
        proposal,
        new_entries_this_week=new_entries_this_week,
    )
    return EvaluationResult(signal=signal, decision=decision, risk=risk)
