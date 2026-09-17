"""Deterministic decision rules for Sentinel Alpha signals."""

from dataclasses import dataclass

from .models import Signal


@dataclass(frozen=True)
class Decision:
    status: str
    confirmation_count: int
    strong_alert: bool
    blocked: bool
    requires_human_approval: bool
    reasons: tuple[str, ...]


def evaluate_signal(signal: Signal, minimum_confirmations: int = 2) -> Decision:
    """Evaluate a signal without placing or authorizing any trade.

    Strong alerts require independent confirmations. Conflicting evidence blocks
    escalation. Every actionable result remains subject to human approval.
    """
    confirmation_count = len(set(signal.confirmations))
    reasons: list[str] = []

    if signal.conflicts:
        reasons.append("conflicting_evidence")

    if confirmation_count < minimum_confirmations:
        reasons.append("insufficient_independent_confirmations")

    blocked = bool(signal.conflicts) or confirmation_count < minimum_confirmations
    strong_alert = not blocked and signal.status.lower() in {"alert", "strong", "confirmed"}

    if strong_alert:
        reasons.append("minimum_confirmation_threshold_met")

    return Decision(
        status=signal.status,
        confirmation_count=confirmation_count,
        strong_alert=strong_alert,
        blocked=blocked,
        requires_human_approval=True,
        reasons=tuple(reasons),
    )
