"""Bridge SEC filing documents into fail-closed semantic evidence roles."""

from .eightk_facts import parse_explicit_adverse_8k_facts
from .eightk_parser import parse_8k_events
from .evidence_roles import ClassifiedEvidence, classify_sec_record
from .form4_parser import parse_form4_transactions
from .provenance import NormalizedRecord
from .sec_semantics import classify_8k, classify_form4


def classify_sec_document(
    record: NormalizedRecord,
    *,
    form: str,
    document: str,
) -> tuple[ClassifiedEvidence, ...]:
    """Parse one SEC document and classify extracted facts fail closed.

    Explicit content-specific adverse 8-K facts may create CONFLICT. Item-number
    taxonomy alone remains UNKNOWN/CONTEXT. Parsing never creates SUPPORT under
    sec-v1.
    """
    if record.source.independence_key != "sec":
        raise ValueError("SEC document classification requires SEC-provenanced evidence")

    if form.startswith("4"):
        facts = parse_form4_transactions(document)
        if facts:
            return tuple(classify_form4(record, fact) for fact in facts)
    elif form.startswith("8-K"):
        adverse = parse_explicit_adverse_8k_facts(document)
        if adverse:
            return tuple(classify_8k(record, event) for event in adverse)
        events = parse_8k_events(document)
        if events:
            return tuple(classify_8k(record, event) for event in events)

    return (classify_sec_record(record),)
