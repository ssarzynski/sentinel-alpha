from __future__ import annotations

from dataclasses import dataclass

from app.services.signal_intelligence import SignalIntelligence


@dataclass(frozen=True)
class SignalPriority:
    asset: str
    attention_score: int
    priority: str
    eligible_for_alert: bool
    human_review_required: bool
    reasons: tuple[str, ...]


def prioritize_signal(signal: SignalIntelligence) -> SignalPriority:
    """Prioritize analyst attention without weakening confirmation or trade controls.

    The score is descriptive workflow triage. It cannot make an unconfirmed signal
    alert-eligible and never authorizes or executes a financial action.
    """
    reasons: list[str] = []
    score = 0

    if signal.state == "confirmed_review" and signal.confirmation_count >= 2:
        score += 60
        reasons.append("independent_confirmation_gate_met")
    elif signal.state == "developing":
        score += min(signal.confirmation_count, 1) * 25
        reasons.append("developing_signal")
    elif signal.state == "withheld":
        reasons.append("withheld_by_evidence_quality_gate")
    else:
        reasons.append("no_actionable_evidence")

    # Additional independent families can raise review urgency only after the gate.
    if signal.state == "confirmed_review" and signal.confirmation_count > 2:
        bonus = min((signal.confirmation_count - 2) * 10, 20)
        score += bonus
        reasons.append("additional_independent_confirmation")

    # Insider selling is a risk warning, not positive confirmation or conviction.
    if signal.insider_sale_warning:
        score += 10
        reasons.append("insider_sale_review_warning")

    score = min(score, 100)
    eligible = signal.state == "confirmed_review" and signal.confirmation_count >= 2
    if not eligible:
        priority = "withheld" if signal.state == "withheld" else "monitor"
    elif score >= 80:
        priority = "high_review"
    else:
        priority = "review"

    return SignalPriority(
        asset=signal.asset,
        attention_score=score,
        priority=priority,
        eligible_for_alert=eligible,
        human_review_required=eligible,
        reasons=tuple(reasons),
    )
