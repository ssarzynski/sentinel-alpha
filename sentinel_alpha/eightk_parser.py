"""Extract 8-K item-number facts without guessing sentiment."""

import re
from html import unescape

from .sec_semantics import EightKEvent, EightKEventKind

_ITEM_PATTERN = re.compile(r"\bItem\s+(\d\.\d{2})\b", re.IGNORECASE)
_TAG_PATTERN = re.compile(r"<[^>]+>")


def parse_8k_events(document: str) -> tuple[EightKEvent, ...]:
    """Return unique parsed 8-K items in document order.

    HTML tags/entities are normalized before matching. An item number is filing
    taxonomy, not evidence of directional meaning, so item-only facts remain
    UNKNOWN until a content-specific semantic rule identifies the event.
    """
    text = unescape(_TAG_PATTERN.sub(" ", document))
    seen: set[str] = set()
    parsed: list[EightKEvent] = []
    for match in _ITEM_PATTERN.finditer(text):
        item = match.group(1)
        if item in seen:
            continue
        seen.add(item)
        parsed.append(EightKEvent(kind=EightKEventKind.UNKNOWN, item=item))
    return tuple(parsed)
