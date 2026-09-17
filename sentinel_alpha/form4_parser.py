"""Extract transaction facts from SEC Form 4 ownership XML."""

import xml.etree.ElementTree as ET

from .sec_semantics import Form4Transaction, Form4TransactionKind

_CODE_KIND = {
    "P": Form4TransactionKind.PURCHASE,
    "S": Form4TransactionKind.SALE,
    "A": Form4TransactionKind.AWARD,
}


def _name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(element: ET.Element, wanted: str) -> str | None:
    for child in element.iter():
        if _name(child.tag) == wanted and child.text:
            value = child.text.strip()
            if value:
                return value
    return None


def parse_form4_transactions(document: str) -> tuple[Form4Transaction, ...]:
    """Return parsed non-derivative transactions; malformed XML fails closed."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError:
        return ()

    parsed: list[Form4Transaction] = []
    for element in root.iter():
        if _name(element.tag) != "nonDerivativeTransaction":
            continue
        code = _find_text(element, "transactionCode")
        if not code:
            continue
        normalized = code.upper()
        parsed.append(
            Form4Transaction(
                kind=_CODE_KIND.get(normalized, Form4TransactionKind.OTHER),
                transaction_code=normalized,
            )
        )
    return tuple(parsed)
