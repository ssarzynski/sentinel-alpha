"""End-to-end Sentinel Alpha evaluation pipeline."""

from dataclasses import dataclass

from .decision_engine import Decision, evaluate_signal
from .macro_regime import MacroRegime, MacroRegimeResult
from .models import Signal
from .provenance import NormalizedRecord, independent_confirmation_keys
from .risk_gate import RiskGateResult, TradeProposal, evaluate_risk_gate


@dataclass(frozen=True)
class EvaluationResult:
    signal: Signal
    decision: Decision
    risk: RiskGateResult
    macro: MacroRegimeResult | None = None


def evaluate_records(
    *,
    asset: str,
    status: str,
    records: list[NormalizedRecord],
    proposal: TradeProposal,
    new_entries_this_week: int,
    conflicts: list[str] | None = None,
    macro: MacroRegimeResult | None = None,
) -> EvaluationResult:
    """Evaluate normalized evidence through confirmation and risk controls.

    Macro regime is contextual evidence only. It cannot create confirmations,
    authorize execution, or bypass any risk gate. UNKNOWN macro context fails
    closed by adding a conflict; risk-off context is surfaced as a conflict for
    human review rather than silently changing the evidence count.
    """
    effective_conflicts = list(conflicts or [])
    if macro is not None:
        if not macro.usable:
            effective_conflicts.append("macro_context_unavailable")
        elif macro.regime is MacroRegime.RISK_OFF:
            effective_conflicts.append("macro_regime_risk_off")

    confirmation_keys = sorted(independent_confirmation_keys(records))
    evidence = [record.evidence for record in records]
    signal = Signal(
        asset=asset.strip().upper(),
        status=status,
        confirmations=confirmation_keys,
        conflicts=effective_conflicts,
        evidence=evidence,
    )
    decision = evaluate_signal(signal)
    risk = evaluate_risk_gate(
        decision,
        proposal,
        new_entries_this_week=new_entries_this_week,
    )
    return EvaluationResult(signal=signal, decision=decision, risk=risk, macro=macro)
