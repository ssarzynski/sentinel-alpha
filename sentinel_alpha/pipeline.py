"""End-to-end Sentinel Alpha evaluation pipeline."""

from dataclasses import dataclass

from .decision_engine import Decision, evaluate_signal
from .evidence_roles import ClassifiedEvidence, EvidenceRole, classify_uninterpreted
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
    classified_evidence: list[ClassifiedEvidence] | None = None,
) -> EvaluationResult:
    """Evaluate evidence through semantic confirmation and risk controls.

    Only explicitly classified SUPPORT evidence may create independent
    confirmations. Unclassified raw records fail closed as CONTEXT. WARNING and
    CONTEXT evidence remain visible in the signal evidence trail but cannot
    manufacture confirmation; CONFLICT evidence blocks through the existing
    decision engine. Macro context likewise cannot create confirmations.
    """
    effective_conflicts = list(conflicts or [])
    if macro is not None:
        if not macro.usable:
            effective_conflicts.append("macro_context_unavailable")
        elif macro.regime is MacroRegime.RISK_OFF:
            effective_conflicts.append("macro_regime_risk_off")

    classified = (
        list(classified_evidence)
        if classified_evidence is not None
        else [classify_uninterpreted(record) for record in records]
    )
    raw_ids = {id(record) for record in records}
    if any(id(item.record) not in raw_ids for item in classified):
        raise ValueError("classified evidence must refer to records in this evaluation")

    support_records = [item.record for item in classified if item.role is EvidenceRole.SUPPORT]
    for item in classified:
        if item.role is EvidenceRole.CONFLICT:
            effective_conflicts.append(item.rationale)

    confirmation_keys = sorted(independent_confirmation_keys(support_records))
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
