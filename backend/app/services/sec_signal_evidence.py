from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.form4 import InsiderTransaction, classify_transaction
from app.models import Evidence
from app.signal_evaluation import EvidenceConfirmation


@dataclass(frozen=True)
class SecSignalEvidence:
    confirmations: tuple[EvidenceConfirmation, ...]
    evidence_ids: tuple[int, ...]
    insider_selling_warning: bool


def normalized_form4_payload(transaction: InsiderTransaction) -> dict[str, object]:
    """Produce the normalized subset used by the signal layer.

    Only discretionary, non-derivative open-market P/S transactions are signal
    eligible. Other Form 4 activity remains evidence but cannot masquerade as an
    open-market insider trade.
    """
    classification = classify_transaction(transaction)
    return {
        "form": "4",
        "transaction_code": transaction.transaction_code.upper().strip(),
        "transaction_direction": classification.direction,
        "economic_type": classification.economic_type,
        "signal_eligible": classification.signal_eligible,
        "owner_name": transaction.owner_name,
        "owner_roles": list(transaction.owner_roles),
        "shares": str(transaction.shares) if transaction.shares is not None else None,
        "price_per_share": str(transaction.price_per_share) if transaction.price_per_share is not None else None,
        "is_derivative": transaction.is_derivative,
        "classification_reasons": list(classification.reasons),
    }


def _eligible_form4(evidence: Evidence) -> bool:
    payload = evidence.payload_json or {}
    if str(payload.get("form", "")).upper() != "4":
        return True
    return bool(payload.get("signal_eligible", False))


def _is_form4_sale(evidence: Evidence) -> bool:
    payload = evidence.payload_json or {}
    return (
        str(payload.get("form", "")).upper() == "4"
        and bool(payload.get("signal_eligible", False))
        and str(payload.get("economic_type", "")).lower() == "open_market_sale"
        and str(payload.get("transaction_direction", "")).lower() == "sell"
    )


def sec_signal_evidence(db: Session, asset: str, *, limit: int = 100) -> SecSignalEvidence:
    rows = list(db.scalars(select(Evidence).where(Evidence.asset == asset.upper(), Evidence.category == "regulatory_filing").order_by(Evidence.observed_at.desc(), Evidence.id.desc()).limit(limit)).all())
    eligible = [row for row in rows if _eligible_form4(row)]
    confirmations = tuple(EvidenceConfirmation(source_family=row.source_family, accepted=True) for row in eligible)
    return SecSignalEvidence(
        confirmations=confirmations,
        evidence_ids=tuple(row.id for row in rows),
        insider_selling_warning=any(_is_form4_sale(row) for row in rows),
    )
