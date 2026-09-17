"""Semantic evidence roles for confirmation-safe evaluation."""

from dataclasses import dataclass
from enum import Enum

from .provenance import NormalizedRecord


class EvidenceRole(str, Enum):
    """How a normalized observation participates in a candidate decision."""

    SUPPORT = "support"
    WARNING = "warning"
    CONTEXT = "context"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class ClassifiedEvidence:
    """A raw normalized record plus an explicit semantic decision role."""

    record: NormalizedRecord
    role: EvidenceRole
    rationale: str

    def __post_init__(self) -> None:
        if not self.rationale.strip():
            raise ValueError("classified evidence requires a rationale")


def classify_uninterpreted(record: NormalizedRecord) -> ClassifiedEvidence:
    """Fail closed: raw observations are context until semantics are established."""
    return ClassifiedEvidence(
        record=record,
        role=EvidenceRole.CONTEXT,
        rationale="raw observation has not been semantically classified as candidate support",
    )


def classify_sec_record(record: NormalizedRecord) -> ClassifiedEvidence:
    """Keep raw SEC 8-K/Form 4 observations out of confirmation counts.

    Filing existence alone does not establish direction. Form 4 can represent a
    purchase, sale, award, or other transaction; an 8-K can contain positive,
    negative, or neutral events. Transaction/event parsing belongs in a later
    semantic classifier. Insider selling remains warning-only once identified.
    """
    if record.source.independence_key != "sec":
        raise ValueError("SEC classifier requires SEC-provenanced evidence")
    return ClassifiedEvidence(
        record=record,
        role=EvidenceRole.CONTEXT,
        rationale="raw SEC filing existence is directional context, not candidate support",
    )
