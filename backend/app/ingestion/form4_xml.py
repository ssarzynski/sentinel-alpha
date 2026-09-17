from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from app.ingestion.form4 import InsiderTransaction


def _text(node: ET.Element | None, path: str) -> str | None:
    if node is None:
        return None
    found = node.find(path)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal value in Form 4 XML: {value}") from exc


def _roles(owner: ET.Element) -> tuple[str, ...]:
    relationship = owner.find("reportingOwnerRelationship")
    if relationship is None:
        return ()
    roles: list[str] = []
    flags = [
        ("isDirector", "director"),
        ("isOfficer", "officer"),
        ("isTenPercentOwner", "10% owner"),
        ("isOther", "other"),
    ]
    for tag, label in flags:
        if (_text(relationship, tag) or "0").lower() in {"1", "true"}:
            roles.append(label)
    officer_title = _text(relationship, "officerTitle")
    if officer_title:
        roles.append(officer_title)
    return tuple(dict.fromkeys(roles))


def parse_form4_xml(xml_text: str, *, ticker: str | None = None) -> list[InsiderTransaction]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("invalid Form 4 XML") from exc

    issuer = _text(root, "issuer/issuerName") or "UNKNOWN"
    xml_ticker = _text(root, "issuer/issuerTradingSymbol")
    resolved_ticker = (ticker or xml_ticker)

    owners = root.findall("reportingOwner")
    if not owners:
        raise ValueError("Form 4 XML contains no reporting owner")

    # A Form 4 can contain multiple reporting owners. Transactions apply to the
    # filing; emit one normalized transaction per owner so cluster logic can
    # reason about distinct people without losing provenance.
    results: list[InsiderTransaction] = []
    for owner in owners:
        owner_name = _text(owner, "reportingOwnerId/rptOwnerName") or "UNKNOWN"
        roles = _roles(owner)

        for node in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
            results.append(_parse_transaction(node, issuer, resolved_ticker, owner_name, roles, False))
        for node in root.findall("derivativeTable/derivativeTransaction"):
            results.append(_parse_transaction(node, issuer, resolved_ticker, owner_name, roles, True))
    return results


def _parse_transaction(
    node: ET.Element,
    issuer: str,
    ticker: str | None,
    owner_name: str,
    roles: tuple[str, ...],
    derivative: bool,
) -> InsiderTransaction:
    code = _text(node, "transactionCoding/transactionCode") or ""
    ad = _text(node, "transactionAmounts/transactionAcquiredDisposedCode/value") or ""
    shares = _decimal(_text(node, "transactionAmounts/transactionShares/value"))
    price = _decimal(_text(node, "transactionAmounts/transactionPricePerShare/value"))
    ownership = _text(node, "ownershipNature/directOrIndirectOwnership/value")
    footnotes = tuple(
        ref.attrib["id"]
        for ref in node.findall(".//footnoteId")
        if ref.attrib.get("id")
    )
    return InsiderTransaction(
        issuer=issuer,
        ticker=ticker.upper() if ticker else None,
        owner_name=owner_name,
        owner_roles=roles,
        transaction_code=code,
        acquired_disposed=ad,
        shares=shares,
        price_per_share=price,
        direct_or_indirect=ownership,
        is_derivative=derivative,
        footnotes=footnotes,
    )
