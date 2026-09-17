from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.ingestion.form4 import InsiderClassification, InsiderTransaction, classify_transaction, role_weight


@dataclass(frozen=True)
class ClassifiedInsiderEvent:
    transaction: InsiderTransaction
    classification: InsiderClassification
    filed_at: datetime


@dataclass(frozen=True)
class InsiderCluster:
    ticker: str
    direction: str
    distinct_insiders: int
    transaction_count: int
    aggregate_value: Decimal | None
    max_role_weight: float
    window_days: int
    signal_eligible: bool


def classify_event(transaction: InsiderTransaction, filed_at: datetime) -> ClassifiedInsiderEvent:
    if filed_at.tzinfo is None:
        raise ValueError("filed_at must be timezone-aware")
    return ClassifiedInsiderEvent(transaction, classify_transaction(transaction), filed_at)


def detect_cluster(events: list[ClassifiedInsiderEvent], *, window_days: int = 30, min_insiders: int = 2) -> InsiderCluster | None:
    if window_days <= 0 or min_insiders < 2:
        raise ValueError("cluster parameters are invalid")
    eligible = [e for e in events if e.classification.signal_eligible and e.transaction.ticker]
    if not eligible:
        return None
    ticker = eligible[0].transaction.ticker.upper()
    direction = eligible[0].classification.direction
    eligible = [e for e in eligible if e.transaction.ticker.upper() == ticker and e.classification.direction == direction]
    if not eligible:
        return None
    latest = max(e.filed_at for e in eligible)
    cutoff = latest - timedelta(days=window_days)
    window = [e for e in eligible if e.filed_at >= cutoff]
    insiders = {e.transaction.owner_name.strip().lower() for e in window}
    if len(insiders) < min_insiders:
        return None
    values = [e.transaction.shares * e.transaction.price_per_share for e in window if e.transaction.shares is not None and e.transaction.price_per_share is not None]
    return InsiderCluster(
        ticker=ticker,
        direction=direction,
        distinct_insiders=len(insiders),
        transaction_count=len(window),
        aggregate_value=sum(values, Decimal("0")) if values else None,
        max_role_weight=max(role_weight(e.transaction.owner_roles) for e in window),
        window_days=window_days,
        signal_eligible=True,
    )
