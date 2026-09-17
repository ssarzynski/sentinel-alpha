"""Versioned, fail-closed semantic classification for SEC filing facts.

This module classifies parsed facts, not filing existence. Raw 8-K/Form 4
records remain CONTEXT until a parser supplies explicit transaction/event facts.
"""

from dataclasses import dataclass
from enum import Enum

from .evidence_roles import ClassifiedEvidence, EvidenceRole
from .provenance import NormalizedRecord

SEC_SEMANTIC_RULE_VERSION = "sec-v1"


class Form4TransactionKind(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    AWARD = "award"
    OTHER = "other"


@dataclass(frozen=True)
class Form4Transaction:
    kind: Form4TransactionKind
    transaction_code: str


class EightKEventKind(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EightKEvent:
    kind: EightKEventKind
    item: str


def _require_sec(record: NormalizedRecord) -> None:
    if record.source.independence_key != "sec":
        raise ValueError("SEC semantic classifier requires SEC-provenanced evidence")


def classify_form4(record: NormalizedRecord, transaction: Form4Transaction) -> ClassifiedEvidence:
    """Classify an explicitly parsed Form 4 transaction.

    sec-v1 deliberately does not promote insider purchases to SUPPORT yet.
    Purchases/awards/other transactions remain context until a separately
    calibrated rule exists. Sales are WARNING only and never confirmations.
    """
    _require_sec(record)
    if transaction.kind is Form4TransactionKind.SALE:
        role = EvidenceRole.WARNING
    else:
        role = EvidenceRole.CONTEXT
    return ClassifiedEvidence(
        record,
        role,
        f"{SEC_SEMANTIC_RULE_VERSION}: Form 4 {transaction.kind.value} "
        f"transaction code {transaction.transaction_code}; role={role.value}",
    )


def classify_8k(record: NormalizedRecord, event: EightKEvent) -> ClassifiedEvidence:
    """Classify an explicitly parsed 8-K event without inventing support.

    Negative events are conflicts. Positive, neutral, and unknown events remain
    context in sec-v1 until event-specific support rules are calibrated.
    """
    _require_sec(record)
    role = EvidenceRole.CONFLICT if event.kind is EightKEventKind.NEGATIVE else EvidenceRole.CONTEXT
    return ClassifiedEvidence(
        record,
        role,
        f"{SEC_SEMANTIC_RULE_VERSION}: 8-K item {event.item} classified "
        f"{event.kind.value}; role={role.value}",
    )
