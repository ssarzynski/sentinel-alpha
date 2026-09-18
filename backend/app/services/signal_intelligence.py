from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable


@dataclass(frozen=True)
class EvidenceFact:
    asset: str
    source_family: str
    observed_at: datetime
    signal_eligible: bool = True
    insider_sale: bool = False


@dataclass(frozen=True)
class SignalIntelligence:
    asset: str
    evidence_count: int
    confirmation_count: int
    source_families: tuple[str, ...]
    state: str
    human_review_required: bool
    insider_sale_warning: bool
    reasons: tuple[str, ...]


def aggregate_signal_intelligence(
    asset: str,
    evidence: Iterable[EvidenceFact],
    *,
    now: datetime,
    max_age: timedelta = timedelta(days=7),
    min_confirmations: int = 2,
) -> SignalIntelligence:
    """Aggregate signal evidence without treating duplicate sources as confirmation.

    `confirmation_count` is the number of distinct source families among fresh,
    signal-eligible evidence. Multiple SEC filings/transactions therefore remain
    one confirmation family. This service never executes or authorizes a trade.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if max_age <= timedelta(0) or min_confirmations < 2:
        raise ValueError("signal aggregation parameters are invalid")

    target = asset.upper().strip()
    rows = [row for row in evidence if row.asset.upper().strip() == target]
    fresh = [row for row in rows if row.signal_eligible and row.observed_at.tzinfo is not None and timedelta(0) <= now - row.observed_at <= max_age]
    families = tuple(sorted({row.source_family.strip().upper() for row in fresh if row.source_family.strip()}))
    confirmations = len(families)
    reasons: list[str] = []

    if not rows:
        state = "no_evidence"
        reasons.append("no_evidence")
    elif not fresh:
        state = "withheld"
        reasons.append("no_fresh_signal_eligible_evidence")
    elif confirmations < min_confirmations:
        state = "developing"
        reasons.append("fewer_than_two_independent_evidence_confirmations")
    else:
        state = "confirmed_review"
        reasons.append("independent_confirmation_threshold_met")

    insider_warning = any(row.insider_sale for row in fresh)
    if insider_warning:
        reasons.append("insider_sale_warning")

    return SignalIntelligence(
        asset=target,
        evidence_count=len(rows),
        confirmation_count=confirmations,
        source_families=families,
        state=state,
        human_review_required=state == "confirmed_review",
        insider_sale_warning=insider_warning,
        reasons=tuple(reasons),
    )
