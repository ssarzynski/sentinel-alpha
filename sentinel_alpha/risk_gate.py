"""Sentinel Alpha risk and human-approval gate."""

from dataclasses import dataclass

from .decision_engine import Decision


@dataclass(frozen=True)
class TradeProposal:
    asset: str
    instrument_type: str = "spot"
    leverage: float = 1.0
    stop_loss_defined: bool = False
    insider_selling_warning: bool = False


@dataclass(frozen=True)
class RiskGateResult:
    eligible_for_review: bool
    blocked: bool
    requires_human_approval: bool
    warnings: tuple[str, ...]
    reasons: tuple[str, ...]


def evaluate_risk_gate(
    decision: Decision,
    proposal: TradeProposal,
    *,
    new_entries_this_week: int,
    max_new_entries_per_week: int = 2,
) -> RiskGateResult:
    """Apply non-negotiable Sentinel Alpha risk rules without executing anything."""
    reasons: list[str] = []
    warnings: list[str] = []

    if decision.blocked or not decision.strong_alert:
        reasons.append("signal_not_eligible")

    instrument = proposal.instrument_type.strip().lower()
    if instrument in {"option", "options"}:
        reasons.append("options_prohibited")

    if proposal.leverage > 1.0:
        reasons.append("leverage_prohibited")

    if new_entries_this_week >= max_new_entries_per_week:
        reasons.append("weekly_entry_limit_reached")

    if not proposal.stop_loss_defined:
        reasons.append("risk_control_required_before_entry")

    if proposal.insider_selling_warning:
        warnings.append("insider_selling_warning")

    blocked = bool(reasons)
    return RiskGateResult(
        eligible_for_review=not blocked,
        blocked=blocked,
        requires_human_approval=True,
        warnings=tuple(warnings),
        reasons=tuple(reasons),
    )
