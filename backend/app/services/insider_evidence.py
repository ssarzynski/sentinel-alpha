from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.form4 import InsiderTransaction, classify_transaction, role_weight
from app.ingestion.form4_xml import parse_form4_xml
from app.models import Evidence


def insider_evidence_key(accession_number: str, owner_name: str, transaction_index: int) -> str:
    raw = f"SEC_FORM4:{accession_number}:{owner_name.strip().upper()}:{transaction_index}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _decimal_text(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def create_insider_evidence(
    db: Session,
    *,
    transaction: InsiderTransaction,
    accession_number: str,
    transaction_index: int,
    source_url: str,
    observed_at: datetime,
) -> tuple[Evidence, bool]:
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    if not accession_number.strip() or transaction_index < 0:
        raise ValueError("valid accession number and transaction index are required")
    classification = classify_transaction(transaction)
    key = insider_evidence_key(accession_number, transaction.owner_name, transaction_index)
    existing = db.scalar(select(Evidence).where(Evidence.evidence_key == key))
    if existing:
        return existing, False

    value = None
    if transaction.shares is not None and transaction.price_per_share is not None:
        value = transaction.shares * transaction.price_per_share

    evidence = Evidence(
        evidence_key=key,
        asset=transaction.ticker,
        category="insider_transaction",
        source="SEC_EDGAR_FORM4",
        source_family="SEC",
        source_record_id=accession_number,
        title=f"{transaction.ticker or transaction.issuer} Form 4: {classification.economic_type}",
        source_url=source_url,
        observed_at=observed_at,
        payload_json={
            "issuer": transaction.issuer,
            "ticker": transaction.ticker,
            "owner_name": transaction.owner_name,
            "owner_roles": list(transaction.owner_roles),
            "role_weight": role_weight(transaction.owner_roles),
            "transaction_code": transaction.transaction_code,
            "acquired_disposed": transaction.acquired_disposed,
            "shares": _decimal_text(transaction.shares),
            "price_per_share": _decimal_text(transaction.price_per_share),
            "transaction_value": _decimal_text(value),
            "direct_or_indirect": transaction.direct_or_indirect,
            "is_derivative": transaction.is_derivative,
            "footnotes": list(transaction.footnotes),
            "economic_type": classification.economic_type,
            "direction": classification.direction,
            "discretionary_open_market": classification.discretionary_open_market,
            "signal_eligible": classification.signal_eligible,
            "classification_reasons": list(classification.reasons),
            "transaction_index": transaction_index,
        },
    )
    db.add(evidence)
    db.flush()
    return evidence, True


def ingest_form4_evidence(
    db: Session,
    *,
    xml_text: str,
    accession_number: str,
    source_url: str,
    observed_at: datetime,
    ticker: str | None = None,
) -> list[Evidence]:
    transactions = parse_form4_xml(xml_text, ticker=ticker)
    evidence_rows: list[Evidence] = []
    for index, transaction in enumerate(transactions):
        evidence, _ = create_insider_evidence(
            db,
            transaction=transaction,
            accession_number=accession_number,
            transaction_index=index,
            source_url=source_url,
            observed_at=observed_at,
        )
        evidence_rows.append(evidence)
    return evidence_rows
