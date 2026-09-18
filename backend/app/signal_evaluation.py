from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.data_quality_gate import DataQualityGate
from app.signal_quality_gate import SignalGateResult, gate_signal_level


@dataclass(frozen=True)
class EvidenceConfirmation:
    source_family: str
    accepted: bool = True


@dataclass(frozen=True)
class SignalEvaluation:
    asset: str
    score: float
    requested_level: str
    effective_level: str
    independent_confirmations: int
    market_quality_status: str
    allowed: bool
    human_approval_required: bool
    warnings: tuple[str, ...]
    gate_reasons: tuple[str, ...]


def independent_confirmation_count(evidence: Iterable[EvidenceConfirmation]) -> int:
    """Count accepted, distinct evidence families; duplicate providers do not inflate confirmation."""
    return len({item.source_family.strip().lower() for item in evidence if item.accepted and item.source_family.strip()})


def requested_alert_level(score: float, *, strong_threshold: float = 80.0, watch_threshold: float = 50.0) -> str:
    if strong_threshold <= watch_threshold:
        raise ValueError("strong_threshold must be greater than watch_threshold")
    if score >= strong_threshold:
        return "STRONG"
    if score >= watch_threshold:
        return "WATCH"
    return "NONE"


def evaluate_signal(
    asset: str,
    score: float,
    evidence: Iterable[EvidenceConfirmation],
    market_quality: DataQualityGate,
    *,
    strong_threshold: float = 80.0,
    watch_threshold: float = 50.0,
    insider_selling_warning: bool = False,
) -> SignalEvaluation:
    """Canonical Sentinel signal evaluation path; never creates or executes an order."""
    requested = requested_alert_level(score, strong_threshold=strong_threshold, watch_threshold=watch_threshold)
    confirmations = independent_confirmation_count(evidence)
    gate: SignalGateResult = gate_signal_level(
        requested,
        independent_evidence_confirmations=confirmations,
        market_quality=market_quality,
    )
    warnings: list[str] = []
    if insider_selling_warning:
        warnings.append("insider_selling")
    if market_quality.status == "DEGRADED":
        warnings.append("market_data_degraded")

    return SignalEvaluation(
        asset=asset.strip().upper(),
        score=score,
        requested_level=requested,
        effective_level=gate.effective_level,
        independent_confirmations=confirmations,
        market_quality_status=market_quality.status,
        allowed=gate.allowed,
        human_approval_required=gate.effective_level in {"WATCH", "STRONG"},
        warnings=tuple(warnings),
        gate_reasons=gate.reasons,
    )
