"""Conservative content-specific adverse fact extraction for SEC 8-K documents."""

import re
from html import unescape

from .sec_semantics import EightKEvent, EightKEventKind

_TAG_PATTERN = re.compile(r"<[^>]+>")
_SPACE_PATTERN = re.compile(r"\s+")

# These rules require explicit disclosure language in document content. Filing
# headings and item numbers alone are never directional evidence.
_ADVERSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "4.02",
        re.compile(
            r"\b(?:should\s+no\s+longer\s+be\s+relied\s+upon|"
            r"should\s+not\s+be\s+relied\s+upon)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "3.01",
        re.compile(
            r"\b(?:received\s+(?:a\s+)?notice\s+of\s+delisting|"
            r"failed\s+to\s+satisfy\s+(?:a\s+)?continued\s+listing\s+rule|"
            r"is\s+not\s+in\s+compliance\s+with\s+(?:a\s+)?continued\s+listing\s+standard)\b",
            re.IGNORECASE,
        ),
    ),
)


def _plain_text(document: str) -> str:
    return _SPACE_PATTERN.sub(" ", unescape(_TAG_PATTERN.sub(" ", document))).strip()


def parse_explicit_adverse_8k_facts(document: str) -> tuple[EightKEvent, ...]:
    """Return narrowly recognized adverse facts supported by explicit text.

    This extractor intentionally has high precision and low recall. Unmatched,
    ambiguous, heading-only, or item-number-only text returns no adverse facts
    and therefore cannot create a conflict.
    """
    text = _plain_text(document)
    parsed: list[EightKEvent] = []
    for item, pattern in _ADVERSE_PATTERNS:
        if pattern.search(text):
            parsed.append(EightKEvent(kind=EightKEventKind.NEGATIVE, item=item))
    return tuple(parsed)
