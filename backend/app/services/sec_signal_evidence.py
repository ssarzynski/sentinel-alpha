from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Evidence
from app.signal_evaluation import EvidenceConfirmation


@dataclass(frozen=True)
class SecSignalEvidence:
    confirmations: tuple[EvidenceConfirmation, ...]
    evidence_ids: tuple[int, ...]
    insider_selling_warning: bool


def _is_form4_sale(evidence: Evidence) -> bool:
    """Return true only when normalized evidence explicitly identifies a Form 4 sale.

    Generic Form 4 filings are not assumed to be sales. Transaction parsing can
    set transaction_direction='sale' in payload_json after the filing is parsed.
    """
    payload = evidence.payload_json or {}
    return str(payload.get("form", "")).upper() == "4" and str(payload.get("transaction_direction", "")).lower() == "sale"


def sec_signal_evidence(db: Session, asset: str, *, limit: int = 100) -> SecSignalEvidence:
    rows = list(db.scalars(select(Evidence).where(Evidence.asset == asset.upper(), Evidence.category == "regulatory_filing").order_by(Evidence.observed_at.desc(), Evidence.id.desc()).limit(limit)).all())
    confirmations = tuple(EvidenceConfirmation(source_family=row.source_family, accepted=True) for row in rows)
    return SecSignalEvidence(
        confirmations=confirmations,
        evidence_ids=tuple(row.id for row in rows),
        insider_selling_warning=any(_is_form4_sale(row) for row in rows),
    )
