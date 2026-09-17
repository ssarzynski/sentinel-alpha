"""Extract 8-K item-number facts without guessing sentiment."""

import re
from html import unescape

from .sec_semantics import EightKEvent, EightKEventKind

_ITEM_PATTERN = re.compile(r"\bItem\s+(\d\.\d{2})\b", re.IGNORECASE)
_TAG_PATTERN = re.compile(r"<[^>]+>")

# sec-v1 deliberately recognizes only narrowly defined adverse filing items.
# All other parsed items remain UNKNOWN and therefore CONTEXT.
_NEGATIVE_ITEMS = frozenset({"2.04", "2.06", "3.01", "4.02"})


def parse_8k_events(document: str) -> tuple[EightKEvent, ...]:
    """Return unique parsed 8-K items in document order.

    HTML tags/entities are normalized before matching. Unrecognized or
    non-directional item numbers are UNKNOWN rather than inferred positive.
    """
    text = unescape(_TAG_PATTERN.sub(" ", document))
    seen: set[str] = set()
    parsed: list[EightKEvent] = []
    for match in _ITEM_PATTERN.finditer(text):
        item = match.group(1)
        if item in seen:
            continue
        seen.add(item)
        kind = EightKEventKind.NEGATIVE if item in _NEGATIVE_ITEMS else EightKEventKind.UNKNOWN
        parsed.append(EightKEvent(kind=kind, item=item))
    return tuple(parsed)
