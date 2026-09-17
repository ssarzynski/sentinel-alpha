"""Bridge SEC filing documents into fail-closed semantic evidence roles."""

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
    """Parse one SEC document and classify extracted facts.

    If no recognized facts can be parsed, preserve the raw filing as CONTEXT.
    Parsing never creates SUPPORT under sec-v1.
    """
    if record.source.independence_key != "sec":
        raise ValueError("SEC document classification requires SEC-provenanced evidence")

    if form.startswith("4"):
        facts = parse_form4_transactions(document)
        if facts:
            return tuple(classify_form4(record, fact) for fact in facts)
    elif form.startswith("8-K"):
        events = parse_8k_events(document)
        if events:
            return tuple(classify_8k(record, event) for event in events)

    return (classify_sec_record(record),)
